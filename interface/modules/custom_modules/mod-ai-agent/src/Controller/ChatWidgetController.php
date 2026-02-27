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
     * Green: all current, next > 7 days. Yellow: next due within 7 days. Red: overdue.
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
            SELECT s.id, s.patient_category, s.status, p.medication_name, p.protocol_type
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
            $mStmt = $pdo->prepare("
                SELECT step_name, due_date, window_end, status
                FROM schedule_milestones
                WHERE schedule_id = ? AND status IN ('pending','scheduled','overdue')
                ORDER BY due_date ASC LIMIT 1
            ");
            $mStmt->execute([$sched['id']]);
            $next = $mStmt->fetch();
            $proto = strtoupper($sched['protocol_type'] ?? 'REMS');
            $med = $sched['medication_name'] ?? 'Medication';
            if (($sched['status'] ?? '') === 'paused') {
                $severity = 'blue';
                $bannerLines[] = sprintf(
                    '%s PAUSED — %s — Milestones on hold. Resume to reactivate.',
                    $proto,
                    $med
                );
                continue;
            }
            if (!$next) {
                $bannerLines[] = sprintf(
                    '%s ACTIVE — %s — %s — All milestones complete',
                    $proto,
                    $med,
                    ucfirst($sched['status'])
                );
                continue;
            }
            $due = $next['due_date'] ?? '';
            $wend = $next['window_end'] ?? '';
            $isOverdue = ($due && $due < $today) || ($wend && $wend < $today);
            $daysUntil = $due ? (strtotime($due) - strtotime($today)) / 86400 : 999;
            if ($isOverdue) {
                $severity = 'red';
                $bannerLines[] = sprintf(
                    '%s — ACTION REQUIRED — %s %s overdue (was due %s)',
                    $proto,
                    $med,
                    $next['step_name'] ?? 'milestone',
                    $due
                );
            } elseif ($daysUntil <= 7 && $daysUntil >= 0) {
                if ($severity !== 'red') {
                    $severity = 'yellow';
                }
                $bannerLines[] = sprintf(
                    '%s — %s — %s due in %d days (%s)',
                    $proto,
                    $med,
                    $next['step_name'] ?? 'milestone',
                    (int) $daysUntil,
                    $due
                );
            } else {
                $bannerLines[] = sprintf(
                    '%s ACTIVE — %s — %s — Next: %s due %s',
                    $proto,
                    $med,
                    ucfirst($sched['status']),
                    $next['step_name'] ?? 'milestone',
                    $due
                );
            }
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
            .ctz-chat-fab {
                position: fixed;
                bottom: 1.5rem;
                right: 1.5rem;
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background: var(--primary, #0d6efd);
                color: white;
                border: none;
                box-shadow: 0 4px 12px rgba(0,0,0,.15);
                cursor: pointer;
                z-index: 9998;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5rem;
            }
            .ctz-chat-fab:hover { opacity: 0.9; }
            .ctz-chat-panel {
                display: none;
                position: fixed;
                bottom: 5rem;
                right: 1.5rem;
                width: 380px;
                max-width: calc(100vw - 2rem);
                height: 480px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 8px 24px rgba(0,0,0,.2);
                z-index: 9999;
                flex-direction: column;
                overflow: hidden;
            }
            .ctz-chat-panel.open { display: flex; }
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
            }
            .ctz-chat-header {
                padding: 0.75rem 1rem;
                background: var(--primary, #0d6efd);
                color: white;
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.5rem;
            }
            .ctz-chat-title { flex: 1; }
            .ctz-chat-header-btns {
                display: flex;
                gap: 0.25rem;
                flex-shrink: 0;
            }
            .ctz-header-btn {
                background: rgba(255,255,255,.2);
                border: none;
                color: white;
                width: 28px;
                height: 28px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 1rem;
                line-height: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0;
            }
            .ctz-header-btn:hover { background: rgba(255,255,255,.35); }
            .ctz-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 1rem;
                font-size: 0.9rem;
            }
            .ctz-chat-msg { margin-bottom: 0.75rem; }
            .ctz-chat-msg.user { text-align: right; color: #333; }
            .ctz-chat-msg.assistant { text-align: left; }
            .ctz-chat-msg.assistant .bubble {
                display: inline-block;
                max-width: 90%;
                padding: 0.5rem 0.75rem;
                background: #f0f0f0;
                border-radius: 8px;
                text-align: left;
            }
            .ctz-chat-input-area {
                padding: 0.75rem;
                border-top: 1px solid #dee2e6;
            }
            .ctz-chat-input-area textarea {
                width: 100%;
                min-height: 60px;
                padding: 0.5rem;
                border: 1px solid #ced4da;
                border-radius: 4px;
                resize: none;
            }
            .ctz-chat-input-area button {
                margin-top: 0.5rem;
                padding: 0.4rem 1rem;
            }
            .ctz-chat-tools {
                margin-top: 0.5rem;
                font-size: 0.8rem;
            }
            .ctz-chat-tools-toggle {
                background: none;
                border: none;
                color: var(--primary, #0d6efd);
                cursor: pointer;
                padding: 0.25rem 0;
                text-align: left;
                width: 100%;
            }
            .ctz-chat-tools-toggle:hover { text-decoration: underline; }
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
                border-left: 2px solid #dee2e6;
                margin-bottom: 0.35rem;
                padding: 0.2rem 0 0.2rem 0.5rem;
            }
            .ctz-chat-tools-list .ctz-tool-name { font-weight: 600; }
            .ctz-chat-msg.ctz-thinking .bubble { color: #666; }
            .ctz-thinking-dots::after {
                content: '';
                animation: ctz-dots 1.2s steps(4, end) infinite;
            }
            @keyframes ctz-dots {
                0%, 20% { content: ''; }
                40% { content: '.'; }
                60% { content: '..'; }
                80%, 100% { content: '...'; }
            }
            .ctz-chat-msg.ctz-error .bubble { background: #fff3cd; }
            .ctz-retry-btn { margin-top: 0.5rem; }
            .ctz-starter-wrap { padding: 0.5rem 0; }
            .ctz-starter-wrap.hidden { display: none; }
            .ctz-starter-label { font-size: 0.85rem; color: #666; margin-bottom: 0.5rem; }
            .ctz-starter-btn {
                display: block;
                width: 100%;
                text-align: left;
                padding: 0.5rem 0.75rem;
                margin-bottom: 0.35rem;
                background: #f0f0f0;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.9rem;
            }
            .ctz-starter-btn:hover { background: #e8e8e8; }
            .ctz-msg-time { font-size: 0.7rem; color: #999; margin-top: 0.2rem; }
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
            const COOKIE_OPEN = 'ctz_widget_open';
            const COOKIE_MODE = 'ctz_widget_mode';

            const fab = document.getElementById('ctz-chat-fab');
            const panel = document.getElementById('ctz-chat-panel');
            const messages = document.getElementById('ctz-chat-messages');
            const input = document.getElementById('ctz-chat-input');
            const sendBtn = document.getElementById('ctz-chat-send');
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
            function rebindStarterButtons() {
                const wrap = document.getElementById('ctz-starter-wrap');
                if (wrap) {
                    wrap.querySelectorAll('.ctz-starter-btn').forEach(function(btn) {
                        btn.addEventListener('click', function() {
                            var msg = btn.getAttribute('data-msg');
                            if (msg) { input.value = msg; input.focus(); if (wrap) wrap.classList.add('hidden'); }
                        });
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

            restoreMessagesFromStorage();
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
                var wrap = document.getElementById('ctz-starter-wrap');
                if (wrap) {
                    wrap.querySelectorAll('.ctz-starter-btn').forEach(function(btn) {
                        btn.addEventListener('click', function() {
                            var msg = btn.getAttribute('data-msg');
                            if (msg) {
                                input.value = msg;
                                input.focus();
                                var w = document.getElementById('ctz-starter-wrap');
                                if (w) w.classList.add('hidden');
                            }
                        });
                    });
                }
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
                thinkingBubble.className = 'bubble ctz-thinking-dots';
                thinkingBubble.textContent = 'Thinking';
                thinkingEl.appendChild(thinkingBubble);
                messages.appendChild(thinkingEl);
                messages.scrollTop = messages.scrollHeight;

                var longWaitTimer = setTimeout(function() {
                    if (thinkingBubble && thinkingBubble.parentNode) {
                        thinkingBubble.textContent = 'Still working — checking multiple sources';
                        thinkingBubble.classList.remove('ctz-thinking-dots');
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
