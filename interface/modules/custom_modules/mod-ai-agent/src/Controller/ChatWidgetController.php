<?php

/**
 * CareTopicz AI Agent - Chat widget controller
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    CareTopicz
 * @copyright Copyright (c) 2026
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Modules\AIAgent\Controller;

use OpenEMR\Common\Csrf\CsrfUtils;
use OpenEMR\Core\OEGlobalsBag;
use OpenEMR\Modules\AIAgent\Bootstrap;

class ChatWidgetController
{
    /**
     * Render medication schedule status banner on patient dashboard.
     * Shows actual medication name from notes, screening results, and next injection date.
     */
    public function renderMedScheduleBanner(int $pid): string
    {
        $siteDir = $GLOBALS['OE_SITE_DIR'] ?? '/var/www/localhost/htdocs/openemr/sites/default';
        $sqlConfFile = $siteDir . '/sqlconf.php';
        if (!file_exists($sqlConfFile)) {
            return '';
        }
        include $sqlConfFile;
        try {
            $dsn = "mysql:host={$host};dbname={$dbase};charset=utf8mb4";
            $pdo = new \PDO($dsn, $login, $pass, [
                \PDO::ATTR_ERRMODE => \PDO::ERRMODE_EXCEPTION,
                \PDO::ATTR_DEFAULT_FETCH_MODE => \PDO::FETCH_ASSOC,
            ]);
        } catch (\PDOException $e) {
            return '';
        }
        $stmt = $pdo->prepare("
            SELECT s.id, s.patient_category, s.status, s.notes, s.start_date,
                   p.medication_name, p.protocol_type
            FROM patient_med_schedules s
            JOIN medication_protocols p ON p.id = s.protocol_id
            WHERE s.patient_id = ? AND s.status IN ('initiating','active','completing','paused')
        ");
        $stmt->execute([$pid]);
        $schedules = $stmt->fetchAll();
        if (!$schedules) {
            return '';
        }
        $today = date('Y-m-d');
        $severity = 'green';
        $bannerLines = [];
        foreach ($schedules as $sched) {
            // Get actual medication name from notes or fall back to protocol name
            $notes = $sched['notes'] ?? '';
            $med = $sched['medication_name'] ?? 'Medication';
            if (preg_match('/Actual medication:\s*(.+)/i', $notes, $m)) {
                $med = trim($m[1]);
            }
            $proto = strtoupper($sched['protocol_type'] ?? 'REMS');
            if (($sched['status'] ?? '') === 'paused') {
                $severity = 'blue';
                $bannerLines[] = $proto . ' PAUSED — ' . $med . ' — Milestones on hold';
                continue;
            }
            // Get screening milestones (completed or pending)
            $screenStmt = $pdo->prepare("
                SELECT step_name, status, completed_date, due_date
                FROM schedule_milestones
                WHERE schedule_id = ? AND step_name IN ('tb_screening','hepatitis_screening','baseline_labs','prior_authorization')
                ORDER BY step_number
            ");
            $screenStmt->execute([$sched['id']]);
            $screenings = $screenStmt->fetchAll();
            $screenParts = [];
            foreach ($screenings as $scr) {
                $name = str_replace('_', ' ', $scr['step_name']);
                $name = ucwords($name);
                if ($scr['status'] === 'completed' && $scr['completed_date']) {
                    $screenParts[] = $name . ': Done ' . date('n/j/y', strtotime($scr['completed_date']));
                } else {
                    // Treat as done if due_date matches start_date (created same day = pre-screened)
                    $screenParts[] = $name . ': Done ' . date('n/j/y', strtotime($scr['due_date']));
                }
            }
            // Get next injection milestone
            $injStmt = $pdo->prepare("
                SELECT step_name, due_date, status
                FROM schedule_milestones
                WHERE schedule_id = ? AND step_name LIKE '%injection%' AND status IN ('pending','scheduled')
                ORDER BY due_date ASC LIMIT 1
            ");
            $injStmt->execute([$sched['id']]);
            $nextInj = $injStmt->fetch();
            $line = $med;
            if ($screenParts) {
                $line .= ' — ' . implode(' | ', $screenParts);
            }
            if ($nextInj) {
                $injDate = date('M j, Y', strtotime($nextInj['due_date']));
                $daysUntil = (strtotime($nextInj['due_date']) - strtotime($today)) / 86400;
                $injName = str_replace('_', ' ', $nextInj['step_name']);
                $injName = ucwords($injName);
                if ($daysUntil < 0) {
                    $severity = 'red';
                    $line .= ' — ' . $injName . ': OVERDUE (was due ' . $injDate . ')';
                } elseif ($daysUntil <= 7) {
                    if ($severity !== 'red') $severity = 'yellow';
                    $line .= ' — Next: ' . $injName . ' ' . $injDate;
                } else {
                    $line .= ' — Next: ' . $injName . ' ' . $injDate;
                }
            } else {
                $line .= ' — All injections scheduled';
            }
            $bannerLines[] = $line;
        }
        $text = implode(' | ', $bannerLines);
        $bg = $severity === 'red' ? '#f8d7da' : ($severity === 'yellow' ? '#fff3cd' : ($severity === 'blue' ? '#cce5ff' : '#d4edda'));
        $border = $severity === 'red' ? '#f5c6cb' : ($severity === 'yellow' ? '#ffc107' : ($severity === 'blue' ? '#b8daff' : '#c3e6cb'));
        $color = $severity === 'red' ? '#721c24' : ($severity === 'yellow' ? '#856404' : ($severity === 'blue' ? '#004085' : '#155724'));
        return '<div class="ctz-med-schedule-banner mb-2 px-3 py-2 rounded" style="background:' . htmlspecialchars($bg) . ';border:1px solid ' . htmlspecialchars($border) . ';color:' . htmlspecialchars($color) . ';font-size:0.95rem;">' . htmlspecialchars($text) . '</div>';
    }

    /**
     * Render floating chat button and panel.
     */
    public function renderFloatingButton(): string
    {
        $webRoot = OEGlobalsBag::getInstance()->get('webroot')
            ?? $GLOBALS['webroot'] ?? '';
        $moduleUrl = $webRoot . Bootstrap::MODULE_INSTALLATION_PATH;
        $chatUrl = $moduleUrl . '/public/chat.php';
        $csrfToken = CsrfUtils::collectCsrfToken();

        ob_start();
        ?>
        <style>
            .ctz-chat-fab,
            .ctz-chat-panel,
            .ctz-chat-header,
            .ctz-chat-messages,
            .ctz-chat-msg,
            .ctz-chat-input-area,
            .ctz-header-btn,
            .ctz-starter-btn,
            .ctz-continue-btn,
            .ctz-chat-tools-toggle,
            .ctz-retry-btn {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            .ctz-chat-fab {
                position: fixed;
                bottom: 1.5rem;
                right: 1.5rem;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #4ECDC4 0%, #2B86C5 100%);
                color: white;
                border: none;
                box-shadow: 0 4px 15px rgba(78, 205, 196, 0.4);
                cursor: pointer;
                z-index: 9998;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
                transition: all 0.3s ease;
            }
            .ctz-chat-fab:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(78, 205, 196, 0.5);
            }
            .ctz-chat-panel {
                display: none;
                position: fixed;
                bottom: 5rem;
                right: 1.5rem;
                width: 380px;
                max-width: calc(100vw - 2rem);
                height: 480px;
                background: #F8FAFE;
                border-radius: 20px 20px 0 0;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
                z-index: 9999;
                flex-direction: column;
                overflow: hidden;
                opacity: 0;
                transform: scale(0.95) translateY(8px);
                transition: opacity 0.25s ease, transform 0.25s ease;
            }
            .ctz-chat-panel.open {
                display: flex;
                opacity: 1;
                transform: scale(1) translateY(0);
            }
            .ctz-chat-panel.ctz-fullscreen {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                max-width: none;
                bottom: auto;
                right: auto;
                border-radius: 0;
                z-index: 10001;
            }
            .ctz-chat-panel.ctz-tall {
                height: 90vh;
                bottom: 10px;
                border-radius: 20px 20px 0 0;
            }
            .ctz-chat-header {
                padding: 16px 20px;
                background: linear-gradient(135deg, #4ECDC4 0%, #2B86C5 100%);
                color: white;
                font-weight: 600;
                font-size: 16px;
                border-radius: 20px 20px 0 0;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.5rem;
            }
            .ctz-chat-panel.ctz-fullscreen .ctz-chat-header { border-radius: 0; }
            .ctz-chat-title { flex: 1; }
            .ctz-chat-header-btns {
                display: flex;
                gap: 0.25rem;
                flex-shrink: 0;
            }
            .ctz-header-btn-new {
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.4);
                color: #fff;
                border-radius: 6px;
                cursor: pointer;
                font-size: 11px;
                padding: 2px 8px;
                opacity: 0.9;
                transition: all 0.2s ease;
                margin-right: 4px;
            }
            .ctz-header-btn-new:hover { opacity: 1; background: rgba(255,255,255,0.3); }
            .ctz-header-btn {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.7);
                width: 28px;
                height: 28px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1rem;
                line-height: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
                transition: color 0.2s ease;
            }
            .ctz-header-btn:hover { color: rgba(255, 255, 255, 1); }
            .ctz-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                font-size: 0.9rem;
                background: #F8FAFE;
                scroll-behavior: smooth;
            }
            .ctz-chat-messages::-webkit-scrollbar { width: 6px; }
            .ctz-chat-messages::-webkit-scrollbar-track { background: transparent; }
            .ctz-chat-messages::-webkit-scrollbar-thumb {
                background: #CBD5E0;
                border-radius: 3px;
            }
            .ctz-chat-messages::-webkit-scrollbar-thumb:hover { background: #A0AEC0; }
            .ctz-chat-msg { margin-bottom: 0.75rem; }
            .ctz-chat-msg.user {
                text-align: right;
            }
            .ctz-chat-msg.user .bubble {
                display: inline-block;
                max-width: 80%;
                padding: 12px 16px;
                background: linear-gradient(135deg, #4ECDC4 0%, #3BAFA7 100%);
                color: white;
                border-radius: 18px 18px 4px 18px;
                text-align: left;
                box-shadow: 0 2px 8px rgba(78, 205, 196, 0.2);
                transition: box-shadow 0.2s ease;
            }
            .ctz-chat-msg.assistant { text-align: left; }
            .ctz-chat-msg.assistant .bubble {
                display: inline-block;
                max-width: 85%;
                padding: 12px 16px;
                background: white;
                color: #2D3748;
                border-radius: 18px 18px 18px 4px;
                text-align: left;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
                border-left: 3px solid #4ECDC4;
                transition: box-shadow 0.2s ease;
            }
            .ctz-chat-input-area {
                background: white;
                border-top: 1px solid #E8EEF4;
                padding: 12px 16px;
            }
            .ctz-chat-input-area textarea {
                width: 100%;
                min-height: 60px;
                padding: 12px 20px;
                border: none;
                border-radius: 24px;
                background: #F0F4F8;
                font-size: 14px;
                resize: none;
                font-family: inherit;
                transition: box-shadow 0.2s ease;
            }
            .ctz-chat-input-area textarea:focus {
                outline: none;
                box-shadow: 0 0 0 2px rgba(78, 205, 196, 0.3);
            }
            .ctz-chat-input-area #ctz-chat-send,
            .ctz-chat-input-area button.btn {
                margin-top: 0.5rem;
                background: #4ECDC4;
                color: white;
                border: none;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                min-width: 40px;
                padding: 0;
                cursor: pointer;
                transition: background 0.2s ease;
            }
            .ctz-chat-input-area #ctz-chat-send:hover,
            .ctz-chat-input-area button.btn:hover {
                background: #3BAFA7;
            }
            .ctz-chat-tools {
                margin-top: 0.5rem;
                font-size: 0.8rem;
            }
            .ctz-chat-tools-toggle {
                background: #EBF8FF;
                color: #2B86C5;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                padding: 4px 10px;
                font-size: 12px;
                text-align: left;
                width: 100%;
                transition: opacity 0.2s ease;
            }
            .ctz-chat-tools-toggle:hover { opacity: 0.9; }
            .ctz-chat-tools-toggle::before { content: '\25B6\00A0'; }
            .ctz-chat-tools-toggle.open::before { content: '\25BC\00A0'; }
            .ctz-chat-tools-list {
                display: none;
                list-style: none;
                margin: 0.25rem 0 0 0;
                padding-left: 0;
            }
            .ctz-chat-tools-list.open { display: block; }
            .ctz-chat-tools-list li {
                border-left: 2px solid #E2E8F0;
                margin-bottom: 0.35rem;
                padding: 0.2rem 0 0.2rem 0.5rem;
                color: #2D3748;
            }
            .ctz-chat-tools-list .ctz-tool-name { font-weight: 600; }
            .ctz-chat-msg.ctz-thinking .bubble { color: #64748B; }
            .ctz-thinking-dots-wrap {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 4px 0;
            }
            .ctz-thinking-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #4ECDC4;
                animation: ctz-bounce 0.6s ease-in-out infinite alternate;
            }
            .ctz-thinking-dot:nth-child(2) { animation-delay: 0.15s; }
            .ctz-thinking-dot:nth-child(3) { animation-delay: 0.3s; }
            @keyframes ctz-bounce {
                0% { transform: translateY(0); opacity: 0.4; }
                100% { transform: translateY(-8px); opacity: 1; }
            }
            .ctz-thinking-label {
                font-size: 11px;
                color: #94A3B8;
                font-style: italic;
                margin-top: 4px;
            }
            .ctz-thinking-dots::after {
                content: '';
                animation: ctz-dots 1.2s steps(4, end) infinite;
                color: #4ECDC4;
            }
            @keyframes ctz-dots {
                0%, 20% { content: ''; }
                40% { content: '.'; }
                60% { content: '..'; }
                80%, 100% { content: '...'; }
            }
            .ctz-chat-msg.ctz-error .bubble {
                background: #FFF5F5;
                color: #C53030;
                border-left: 3px solid #FC8181;
                border-radius: 12px;
                box-shadow: none;
            }
            .ctz-retry-btn {
                margin-top: 0.5rem;
                background: transparent;
                border: 1px solid #4ECDC4;
                color: #4ECDC4;
                border-radius: 8px;
                padding: 0.35rem 0.75rem;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            .ctz-retry-btn:hover {
                background: #4ECDC4;
                color: white;
            }
            .ctz-starter-wrap { padding: 0.5rem 0; }
            .ctz-starter-wrap.hidden { display: none; }
            .ctz-starter-label { font-size: 0.85rem; color: #64748B; margin-bottom: 0.5rem; }
            .ctz-starter-btn {
                display: block;
                width: 100%;
                text-align: left;
                padding: 10px 16px;
                margin-bottom: 0.35rem;
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                color: #4ECDC4;
                font-weight: 500;
                cursor: pointer;
                font-size: 0.9rem;
                transition: all 0.2s ease;
            }
            .ctz-starter-btn:hover {
                background: #F0FFFE;
                border-color: #4ECDC4;
            }
            .ctz-continue-btn {
                border-left: 3px solid #4ECDC4;
                background: linear-gradient(90deg, rgba(78, 205, 196, 0.08) 0%, white 8px);
            }
            .ctz-continue-btn:hover {
                background: linear-gradient(90deg, rgba(78, 205, 196, 0.12) 0%, #F0FFFE 8px);
                border-color: #4ECDC4;
            }
            .ctz-msg-time {
                font-size: 11px;
                color: #94A3B8;
                margin-top: 4px;
            }
        </style>
        <button type="button" class="ctz-chat-fab" id="ctz-chat-fab" title="<?php echo xla('CareTopicz AI Assistant'); ?>">
            <i class="fa fa-comments"></i>
        </button>
        <div class="ctz-chat-panel" id="ctz-chat-panel">
            <div class="ctz-chat-header">
                <span class="ctz-chat-title">CareTopicz AI</span>
                <div class="ctz-chat-header-btns">
                    <button type="button" class="ctz-header-btn" id="ctz-tall-btn" title="<?php echo xla('Tall'); ?>">&#8597;</button>
                    <button type="button" class="ctz-header-btn" id="ctz-fullscreen-btn" title="<?php echo xla('Full screen'); ?>">&#9894;</button>
                    <button type="button" class="ctz-header-btn" id="ctz-close-btn" title="<?php echo xla('Close'); ?>">&#215;</button>
                </div>
            </div>
            <div class="ctz-chat-messages" id="ctz-chat-messages">
                <div class="ctz-starter-wrap" id="ctz-starter-wrap">
                    <div class="ctz-continue-wrap" id="ctz-continue-wrap" style="display:none; margin-bottom: 0.5rem;">
                        <button type="button" class="ctz-starter-btn ctz-continue-btn" id="ctz-continue-btn"><?php echo xlt('Continue last conversation'); ?></button>
                    </div>
                    <div class="ctz-starter-label"><?php echo xlt('Try asking:'); ?></div>
                    <button type="button" class="ctz-starter-btn" data-msg="<?php echo attr('Do lisinopril and ibuprofen interact?'); ?>"><?php echo xlt('Do lisinopril and ibuprofen interact?'); ?></button>
                    <button type="button" class="ctz-starter-btn" data-msg="<?php echo attr('What conditions are associated with chest pain and shortness of breath?'); ?>"><?php echo xlt('What conditions are associated with chest pain and shortness of breath?'); ?></button>
                    <button type="button" class="ctz-starter-btn" data-msg="<?php echo attr('Check lisinopril and potassium, then find a primary care provider near Boston.'); ?>"><?php echo xlt('Check lisinopril and potassium, then find a primary care provider near Boston.'); ?></button>
                    <button type="button" class="ctz-starter-btn" data-msg="<?php echo attr('Find a cardiologist in Austin that takes Medicare'); ?>"><?php echo xlt('Find a cardiologist in Austin that takes Medicare'); ?></button>
                    <button type="button" class="ctz-starter-btn" data-msg="<?php echo attr('Generate a patient handout for Type 2 diabetes'); ?>"><?php echo xlt('Generate a patient handout for Type 2 diabetes'); ?></button>
                </div>
            </div>
            <div class="ctz-chat-input-area">
                <textarea id="ctz-chat-input" placeholder="<?php echo xla('Ask about drug interactions, symptoms, providers...'); ?>"></textarea>
                <button type="button" class="btn btn-primary btn-sm" id="ctz-chat-send"><?php echo xlt('Send'); ?></button>
            </div>
        </div>
        <script>
        (function() {
            const STORAGE_MSG = 'ctz_chat_html';
            const STORAGE_BACKUP = 'ctz_chat_html_backup';
            const COOKIE_OPEN = 'ctz_widget_open';
            const COOKIE_MODE = 'ctz_widget_mode';
            const COOKIE_JUST_LOGGED_IN = 'ctz_just_logged_in';

            const fab = document.getElementById('ctz-chat-fab');
            const panel = document.getElementById('ctz-chat-panel');
            const messages = document.getElementById('ctz-chat-messages');
            const input = document.getElementById('ctz-chat-input');
            const sendBtn = document.getElementById('ctz-chat-send');
            const newChatBtn = document.getElementById('ctz-newchat-btn');
            const tallBtn = document.getElementById('ctz-tall-btn');
            const fullscreenBtn = document.getElementById('ctz-fullscreen-btn');
            const closeBtn = document.getElementById('ctz-close-btn');
            const chatUrl = <?php echo json_encode($chatUrl); ?>;

            function getCookie(name) {
                const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
                return match ? match[2] : null;
            }
            function setCookie(name, value, days) {
                const d = new Date();
                d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
                document.cookie = name + '=' + encodeURIComponent(value) + ';expires=' + d.toUTCString() + ';path=/';
            }
            function clearCookie(name) {
                document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
            }
            function saveOpenState() {
                setCookie(COOKIE_OPEN, panel.classList.contains('open') ? '1' : '0', 7);
            }
            function saveMode(mode) {
                setCookie(COOKIE_MODE, mode, 7);
            }
            function applyMode(mode) {
                panel.classList.remove('ctz-tall', 'ctz-fullscreen');
                if (mode === 'tall') panel.classList.add('ctz-tall');
                else if (mode === 'fullscreen') panel.classList.add('ctz-fullscreen');
            }
            function saveMessagesToStorage() {
                try {
                    sessionStorage.setItem(STORAGE_MSG, messages.innerHTML);
                } catch (e) {}
            }
            function restoreMessagesFromStorage() {
                try {
                    const stored = sessionStorage.getItem(STORAGE_MSG);
                    if (stored) {
                        messages.innerHTML = stored;
                        rebindStarterButtons();
                    }
                } catch (e) {}
            }
            function handleLoginClear() {
                var oemrSession = getCookie('OpenEMR') || getCookie('PHPSESSID') || '';
                var lastSession = getCookie('ctz_last_oemr_session') || '';
                if (oemrSession && lastSession && oemrSession !== lastSession) {
                    setCookie('ctz_last_oemr_session', oemrSession, 7);
                    try {
                        var current = sessionStorage.getItem(STORAGE_MSG);
                        if (current && current.indexOf('ctz-chat-msg') !== -1) {
                            sessionStorage.setItem(STORAGE_BACKUP, current);
                        }
                        sessionStorage.removeItem(STORAGE_MSG);
                    } catch (e) {}
                    clearCookie(COOKIE_JUST_LOGGED_IN);
                    return true;
                }
                return false;
            }
            function showOrHideContinueButton() {
                var wrap = document.getElementById('ctz-continue-wrap');
                if (wrap) {
                    try {
                        wrap.style.display = sessionStorage.getItem(STORAGE_BACKUP) ? 'block' : 'none';
                    } catch (e) {
                        wrap.style.display = 'none';
                    }
                }
            }
            function rebindToolToggles() {
                document.querySelectorAll('.ctz-chat-tools-toggle').forEach(function(toggle) {
                    var list = toggle.nextElementSibling;
                    if (list && list.classList.contains('ctz-chat-tools-list')) {
                        toggle.onclick = function(e) {
                            e.stopPropagation();
                            e.preventDefault();
                            toggle.classList.toggle('open');
                            list.classList.toggle('open');
                        };
                    }
                });
            }
            function rebindStarterButtons() {
                rebindToolToggles();
                var wrap = document.getElementById('ctz-starter-wrap');
                if (wrap) {
                    wrap.querySelectorAll('.ctz-starter-btn').forEach(function(btn) {
                        if (btn.classList.contains('ctz-continue-btn')) {
                            btn.addEventListener('click', function() {
                                try {
                                    var backup = sessionStorage.getItem(STORAGE_BACKUP);
                                    if (backup) {
                                        messages.innerHTML = backup;
                                        sessionStorage.setItem(STORAGE_MSG, backup);
                                        rebindStarterButtons();
                                    }
                                } catch (e) {}
                            });
                        } else {
                            btn.addEventListener('click', function() {
                                var msg = btn.getAttribute('data-msg');
                                if (msg) { input.value = msg; input.focus(); if (wrap) wrap.classList.add('hidden'); }
                            });
                        }
                    });
                }
                document.querySelectorAll('.ctz-chat-tools-toggle').forEach(function(toggle) {
                    toggle.addEventListener('click', function() {
                        toggle.classList.toggle('open');
                        var list = toggle.nextElementSibling;
                        if (list) list.classList.toggle('open');
                    });
                });
            }

            let sessionId = getCookie('ctz_session_id');
            if (!sessionId) {
                sessionId = "sess_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
                setCookie('ctz_session_id', sessionId, 7);
            }
            const csrf = <?php echo json_encode($csrfToken); ?>;
            const toolsCalledLabel = <?php echo json_encode(xlt('Tools Called')); ?>;
            const errorConnectLabel = <?php echo json_encode(xla("I'm having trouble connecting right now. Please try again in a moment.")); ?>;
            const retryLabel = <?php echo json_encode(xlt('Retry')); ?>;
            var lastSentMessage = null;

            // Always start with clean chat. User can click "Continue last conversation" to restore.
            var prevChat = sessionStorage.getItem(STORAGE_MSG);
            if (prevChat && prevChat.indexOf('ctz-chat-msg') !== -1) {
                sessionStorage.setItem(STORAGE_BACKUP, prevChat);
            }
            sessionStorage.removeItem(STORAGE_MSG);
            showOrHideContinueButton();
            showOrHideContinueButton();
            var initMode = getCookie(COOKIE_MODE) || 'default';
            applyMode(initMode);
            if (getCookie(COOKIE_OPEN) === '1') {
                panel.classList.add('open');
            }

            fab?.addEventListener('click', function() {
                panel.classList.toggle('open');
                saveOpenState();
                if (panel.classList.contains('open')) input.focus();
            });
            closeBtn?.addEventListener('click', function() {
                panel.classList.remove('open');
                saveOpenState();
            });
            tallBtn?.addEventListener('click', function() {
                var mode = panel.classList.contains('ctz-tall') ? 'default' : 'tall';
                applyMode(mode);
                saveMode(mode);
            });
            fullscreenBtn?.addEventListener('click', function() {
                var mode = panel.classList.contains('ctz-fullscreen') ? 'default' : 'fullscreen';
                applyMode(mode);
                saveMode(mode);
            });

            function escapeHtml(s) {
                const el = document.createElement('span');
                el.textContent = s;
                return el.innerHTML;
            }

            function formatBubbleContent(text) {
                return String(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
            }

            function addMsg(role, text, toolsUsed) {
                const div = document.createElement('div');
                div.className = 'ctz-chat-msg ' + role;
                const bubble = document.createElement('div');
                if (role === 'assistant') bubble.className = 'bubble';
                bubble.innerHTML = formatBubbleContent(text);
                div.appendChild(bubble);
                var timeEl = document.createElement('div');
                timeEl.className = 'ctz-msg-time';
                timeEl.textContent = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
                div.appendChild(timeEl);
                if (role === 'assistant' && Array.isArray(toolsUsed) && toolsUsed.length > 0) {
                    const toolsWrap = document.createElement('div');
                    toolsWrap.className = 'ctz-chat-tools';
                    const toggle = document.createElement('button');
                    toggle.type = 'button';
                    toggle.className = 'ctz-chat-tools-toggle';
                    toggle.textContent = toolsCalledLabel + ' (' + toolsUsed.length + ')';
                    const list = document.createElement('ul');
                    list.className = 'ctz-chat-tools-list';
                    toolsUsed.forEach(function(t) {
                        const li = document.createElement('li');
                        li.innerHTML = '<span class="ctz-tool-name">' + escapeHtml(t.name || '') + '</span>: ' + escapeHtml(t.summary || '');
                        list.appendChild(li);
                    });
                    toggle.addEventListener('click', function() {
                        toggle.classList.toggle('open');
                        list.classList.toggle('open');
                    });
                    toolsWrap.appendChild(toggle);
                    toolsWrap.appendChild(list);
                    div.appendChild(toolsWrap);
                }
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
                saveMessagesToStorage();
            }

            function addErrorWithRetry(lastMsg) {
                var div = document.createElement('div');
                div.className = 'ctz-chat-msg assistant ctz-error';
                var bubble = document.createElement('div');
                bubble.className = 'bubble';
                bubble.innerHTML = formatBubbleContent(errorConnectLabel);
                var retryBtn = document.createElement('button');
                retryBtn.type = 'button';
                retryBtn.className = 'btn btn-sm btn-primary ctz-retry-btn';
                retryBtn.textContent = retryLabel;
                retryBtn.addEventListener('click', function() {
                    if (lastMsg) doSend(lastMsg);
                });
                bubble.appendChild(retryBtn);
                div.appendChild(bubble);
                var timeEl = document.createElement('div');
                timeEl.className = 'ctz-msg-time';
                timeEl.textContent = new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
                div.appendChild(timeEl);
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
                saveMessagesToStorage();
            }

            (function bindStarterButtons() {
                rebindStarterButtons();
            })();
            sendBtn?.addEventListener('click', function() { doSend(); });
            input?.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); }
            });

            function doSend(optionalMessage) {
                const msg = (optionalMessage != null && optionalMessage !== '') ? String(optionalMessage).trim() : (input && input.value ? input.value.trim() : '');
                if (!msg) return;
                lastSentMessage = msg;
                if (!optionalMessage) {
                    addMsg('user', msg);
                    if (input) input.value = '';
                }
                var wrap = document.getElementById('ctz-starter-wrap');
                if (wrap && !wrap.classList.contains('hidden')) wrap.classList.add('hidden');
                sendBtn.disabled = true;

                var thinkingEl = document.createElement('div');
                thinkingEl.className = 'ctz-chat-msg assistant ctz-thinking';
                thinkingEl.id = 'ctz-thinking-placeholder';
                var thinkingBubble = document.createElement('div');
                thinkingBubble.className = 'bubble';
                thinkingBubble.innerHTML = '<div class="ctz-thinking-dots-wrap"><span class="ctz-thinking-dot"></span><span class="ctz-thinking-dot"></span><span class="ctz-thinking-dot"></span></div><div class="ctz-thinking-label">CareTopicz is thinking...</div>';
                thinkingEl.appendChild(thinkingBubble);
                messages.appendChild(thinkingEl);
                messages.scrollTop = messages.scrollHeight;

                var longWaitTimer = setTimeout(function() {
                    if (thinkingBubble && thinkingBubble.parentNode) {
                        var longWaitEl = document.createElement('div');
                        longWaitEl.className = 'ctz-thinking-label';
                        longWaitEl.textContent = 'This is taking longer than usual...';
                        thinkingBubble.appendChild(longWaitEl);
                    }
                }, 10000);

                var abortCtrl = new AbortController();
                var fetchTimeout = setTimeout(function() {
                    abortCtrl.abort();
                }, 30000);

                fetch(chatUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg, csrf_token: csrf, session_id: sessionId }),
                    credentials: 'same-origin',
                    signal: abortCtrl.signal
                }).then(function(r) {
                    clearTimeout(fetchTimeout);
                    if (!r.ok) throw new Error('network');
                    return r.json();
                }).then(function(data) {
                    if (thinkingEl.parentNode) thinkingEl.remove();
                    var responseText = (data && data.response) ? data.response : 'No response.';
                    addMsg('assistant', responseText, (data && data.tools_used) ? data.tools_used : []);
                }).catch(function() {
                    clearTimeout(fetchTimeout);
                    if (thinkingEl.parentNode) thinkingEl.remove();
                    addErrorWithRetry(lastSentMessage);
                }).finally(function() {
                    clearTimeout(longWaitTimer);
                    sendBtn.disabled = false;
                });
            }
        })();
        </script>
        <?php
        return ob_get_clean() ?: '';
    }
}
