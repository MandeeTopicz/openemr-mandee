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
            .ctz-chat-header {
                padding: 0.75rem 1rem;
                background: var(--primary, #0d6efd);
                color: white;
                font-weight: 600;
            }
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
        </style>
        <button type="button" class="ctz-chat-fab" id="ctz-chat-fab" title="<?php echo xla('CareTopicz AI Assistant'); ?>">
            <i class="fa fa-comments"></i>
        </button>
        <div class="ctz-chat-panel" id="ctz-chat-panel">
            <div class="ctz-chat-header"><?php echo xlt('CareTopicz AI Assistant'); ?></div>
            <div class="ctz-chat-messages" id="ctz-chat-messages"></div>
            <div class="ctz-chat-input-area">
                <textarea id="ctz-chat-input" placeholder="<?php echo xla('Ask about drug interactions, symptoms, providers...'); ?>"></textarea>
                <button type="button" class="btn btn-primary btn-sm" id="ctz-chat-send"><?php echo xlt('Send'); ?></button>
            </div>
        </div>
        <script>
        (function() {
            const fab = document.getElementById('ctz-chat-fab');
            const panel = document.getElementById('ctz-chat-panel');
            const messages = document.getElementById('ctz-chat-messages');
            const input = document.getElementById('ctz-chat-input');
            const sendBtn = document.getElementById('ctz-chat-send');
            const chatUrl = <?php echo json_encode($chatUrl); ?>;
            const csrf = <?php echo json_encode($csrfToken); ?>;

            fab?.addEventListener('click', function() {
                panel.classList.toggle('open');
                if (panel.classList.contains('open')) input.focus();
            });

            function addMsg(role, text) {
                const div = document.createElement('div');
                div.className = 'ctz-chat-msg ' + role;
                const bubble = document.createElement('div');
                if (role === 'assistant') bubble.className = 'bubble';
                bubble.innerHTML = text.replace(/\n/g, '<br>');
                div.appendChild(bubble);
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }

            sendBtn?.addEventListener('click', doSend);
            input?.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(); }
            });

            function doSend() {
                const msg = input?.value.trim();
                if (!msg) return;
                addMsg('user', msg);
                input.value = '';
                sendBtn.disabled = true;
                fetch(chatUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: msg, csrf_token: csrf }),
                    credentials: 'same-origin'
                }).then(r => r.json()).then(data => {
                    addMsg('assistant', data.response || data.error || 'No response.');
                }).catch(() => {
                    addMsg('assistant', 'Unable to reach the assistant. Please try again.');
                }).finally(() => { sendBtn.disabled = false; });
            }
        })();
        </script>
        <?php
        return ob_get_clean() ?: '';
    }
}
