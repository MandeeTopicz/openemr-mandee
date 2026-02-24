<?php

/**
 * CareTopicz AI Agent - Chat API controller
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    CareTopicz
 * @copyright Copyright (c) 2026
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Modules\AIAgent\Controller;

use OpenEMR\Common\Acl\AclMain;
use OpenEMR\Common\Csrf\CsrfUtils;
use OpenEMR\Modules\AIAgent\Service\AgentProxyService;

class AgentController
{
    private AgentProxyService $proxy;

    public function __construct()
    {
        $this->proxy = new AgentProxyService();
    }

    /**
     * Handle chat AJAX request. Expects JSON body: {message, session_id?}
     */
    public function handleChat(): void
    {
        header('Content-Type: application/json');

        if (!$this->checkAcl()) {
            http_response_code(403);
            echo json_encode(['error' => 'Access denied']);
            return;
        }

        $input = $this->getJsonInput();
        if (!CsrfUtils::verifyCsrfToken($input['csrf_token'] ?? $_POST['csrf_token'] ?? $_GET['csrf_token'] ?? '')) {
            http_response_code(403);
            echo json_encode(['error' => 'Invalid CSRF token']);
            return;
        }

        $message = trim($input['message'] ?? '');
        $sessionId = !empty($input['session_id']) ? (string) $input['session_id'] : null;

        if ($message === '') {
            http_response_code(400);
            echo json_encode(['error' => 'Message is required']);
            return;
        }

        try {
            $result = $this->proxy->chat($message, $sessionId);
            echo json_encode($result);
        } catch (\Throwable $e) {
            error_log("AIAgent chat error: " . $e->getMessage());
            http_response_code(502);
            echo json_encode([
                'error' => 'Agent service unavailable',
                'response' => 'The AI assistant is temporarily unavailable. Please try again later.',
                'session_id' => null,
            ]);
        }
    }

    private function checkAcl(): bool
    {
        return AclMain::aclCheckCore('patients', 'demo') || AclMain::aclCheckCore('patients', 'hr');
    }

    private function getJsonInput(): array
    {
        $raw = file_get_contents('php://input');
        $decoded = json_decode($raw ?: '{}', true);
        return is_array($decoded) ? $decoded : [];
    }
}
