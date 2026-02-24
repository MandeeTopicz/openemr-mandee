<?php

/**
 * CareTopicz AI Agent Module - Config
 *
 * Loaded in an iframe by the Module Manager when configuring the module.
 * This module has no user-configurable settings; the chat widget appears
 * automatically on enabled pages when the module is active.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    CareTopicz
 * @copyright Copyright (c) 2026
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

require_once dirname(__FILE__, 4) . '/globals.php';

use OpenEMR\Core\Header;

Header::setupHeader();
echo '<p>' . xlt('No configuration required. Enable the module to show the AI chat widget on the patient dashboard.') . '</p>';
