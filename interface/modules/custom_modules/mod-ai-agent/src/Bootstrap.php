<?php

/**
 * CareTopicz AI Agent Module - Bootstrap
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    CareTopicz
 * @copyright Copyright (c) 2026
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Modules\AIAgent;

use OpenEMR\Common\Logging\SystemLogger;
use OpenEMR\Core\OEGlobalsBag;
use OpenEMR\Events\UserInterface\PageHeadingRenderEvent;
use Symfony\Component\EventDispatcher\EventDispatcherInterface;

class Bootstrap
{
    public const MODULE_INSTALLATION_PATH = "/interface/modules/custom_modules/mod-ai-agent";
    public const MODULE_NAME = "mod-ai-agent";

    private SystemLogger $logger;

    public function __construct(
        private readonly EventDispatcherInterface $eventDispatcher
    ) {
        $this->logger = new SystemLogger();
    }

    public function subscribeToEvents(): void
    {
        $this->eventDispatcher->addListener(
            PageHeadingRenderEvent::EVENT_PAGE_HEADING_RENDER,
            $this->renderChatWidget(...),
            10
        );
    }

    public function renderChatWidget(PageHeadingRenderEvent $event): PageHeadingRenderEvent
    {
        $pageId = $event->getPageId();
        $this->logger->error("AIAgent: PageHeadingRenderEvent fired", ['page_id' => $pageId]);

        if (!in_array($pageId, ['core.mrd', 'core.main']) && $pageId !== 'patient-portal') {
            $this->logger->error("AIAgent: Skipping - page_id not matched", ['page_id' => $pageId]);
            return $event;
        }

        if (isset($GLOBALS['ai_agent_enabled']) && !$GLOBALS['ai_agent_enabled']) {
            return $event;
        }

        try {
            $controller = new Controller\ChatWidgetController();
            $html = $controller->renderFloatingButton();
            $event->appendTitleNavContent($html);
            $this->logger->error("AIAgent: Appended chat widget to titleNavContent", ['length' => strlen($html)]);
        } catch (\Throwable $e) {
            $this->logger->error("AIAgent: Error rendering chat widget", ['error' => $e->getMessage()]);
        }

        return $event;
    }
}
