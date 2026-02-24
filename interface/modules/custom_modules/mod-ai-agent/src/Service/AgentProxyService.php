<?php

/**
 * CareTopicz AI Agent - Proxy to Python FastAPI service
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    CareTopicz
 * @copyright Copyright (c) 2026
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Modules\AIAgent\Service;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\GuzzleException;
use GuzzleHttp\Exception\RequestException;

class AgentProxyService
{
    private const DEFAULT_BASE_URL = 'http://host.docker.internal:8000';

    private Client $client;

    public function __construct(?string $baseUrl = null)
    {
        $url = $baseUrl
            ?? (getenv('OPENEMR_AI_AGENT_URL') ?: null)
            ?? ($GLOBALS['ai_agent_base_url'] ?? null)
            ?? self::DEFAULT_BASE_URL;
        $this->client = new Client([
            'base_uri' => rtrim($url, '/') . '/',
            'timeout' => 60.0,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
            ],
        ]);
    }

    /**
     * Send chat message to agent and return response.
     *
     * @param string $message User message
     * @param string|null $sessionId Optional session ID
     * @return array{response: string, session_id: string|null, run_id: string|null, tools_used: list<array{name: string, summary: string}>} Agent response
     * @throws \RuntimeException On HTTP or parse error
     */
    public function chat(string $message, ?string $sessionId = null): array
    {
        $payload = ['message' => $message];
        if ($sessionId !== null) {
            $payload['session_id'] = $sessionId;
        }

        try {
            $response = $this->client->post('chat', [
                'json' => $payload,
            ]);
        } catch (RequestException $e) {
            $body = $e->hasResponse() ? (string) $e->getResponse()->getBody() : $e->getMessage();
            throw new \RuntimeException("Agent request failed: " . $body, 0, $e);
        } catch (GuzzleException $e) {
            throw new \RuntimeException("Agent request failed: " . $e->getMessage(), 0, $e);
        }

        $data = json_decode((string) $response->getBody(), true);
        if (!is_array($data) || !isset($data['response'])) {
            throw new \RuntimeException("Invalid agent response format");
        }

        $toolsUsed = [];
        if (!empty($data['tools_used']) && is_array($data['tools_used'])) {
            foreach ($data['tools_used'] as $t) {
                if (is_array($t) && isset($t['name'])) {
                    $toolsUsed[] = [
                        'name' => (string) $t['name'],
                        'summary' => isset($t['summary']) ? (string) $t['summary'] : '',
                    ];
                }
            }
        }

        return [
            'response' => (string) $data['response'],
            'session_id' => $data['session_id'] ?? null,
            'run_id' => $data['run_id'] ?? null,
            'tools_used' => $toolsUsed,
        ];
    }

    /**
     * Check agent health.
     */
    public function health(): bool
    {
        try {
            $response = $this->client->get('health');
            $data = json_decode((string) $response->getBody(), true);
            return is_array($data) && ($data['status'] ?? '') === 'healthy';
        } catch (GuzzleException $e) {
            return false;
        }
    }
}
