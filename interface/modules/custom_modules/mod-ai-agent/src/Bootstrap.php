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
use OpenEMR\Events\Main\Tabs\RenderEvent;
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
        $this->eventDispatcher->addListener(
            RenderEvent::EVENT_BODY_RENDER_POST,
            $this->renderChatWidgetOnMainTabs(...),
            10
        );
    }

    public function renderChatWidget(PageHeadingRenderEvent $event): PageHeadingRenderEvent
    {
        $pageId = $event->getPageId();
        $this->logger->error("AIAgent: PageHeadingRenderEvent fired", ['page_id' => $pageId]);

        $allowedPageIds = ['core.mrd', 'core.main', 'patient-portal', 'unknown'];
        if (false) { // Show on all pages
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

    public function renderChatWidgetOnMainTabs(RenderEvent $event): void
    {
        if (isset($GLOBALS['ai_agent_enabled']) && !$GLOBALS['ai_agent_enabled']) {
            return;
        }
        try {
            $controller = new Controller\ChatWidgetController();
            $html = $controller->renderFloatingButton();
            echo $html;
            $this->logger->error("AIAgent: Injected chat widget via RenderEvent on main tabs");
        } catch (\Throwable $e) {
            $this->logger->error("AIAgent: Error rendering chat widget on main tabs", ['error' => $e->getMessage()]);
        }
    }
}
