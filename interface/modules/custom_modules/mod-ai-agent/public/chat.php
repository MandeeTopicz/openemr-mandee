<?php

/**
 * CareTopicz AI Agent - Chat AJAX endpoint
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    CareTopicz
 * @copyright Copyright (c) 2026
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

require_once __DIR__ . "/../../../../globals.php";

use OpenEMR\Modules\AIAgent\Controller\AgentController;

$controller = new AgentController();
$controller->handleChat();
