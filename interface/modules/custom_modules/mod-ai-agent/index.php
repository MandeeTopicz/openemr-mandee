<?php

/**
 * CareTopicz AI Agent Module - Entry point
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
echo '<p>' . xlt('CareTopicz AI Agent module is active. Use the floating chat button on the patient dashboard.') . '</p>';
