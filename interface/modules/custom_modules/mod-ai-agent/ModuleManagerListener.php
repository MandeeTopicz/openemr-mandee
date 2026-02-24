<?php

/**
 * CareTopicz AI Agent - Module Manager listener
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    CareTopicz
 * @copyright Copyright (c) 2026
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

use OpenEMR\Core\AbstractModuleActionListener;

class ModuleManagerListener extends AbstractModuleActionListener
{
    public function moduleManagerAction($methodName, $modId, string $currentActionStatus = 'Success'): string
    {
        if (method_exists(self::class, $methodName)) {
            return self::$methodName($modId, $currentActionStatus);
        }
        return $currentActionStatus;
    }

    public static function getModuleNamespace(): string
    {
        return 'OpenEMR\\Modules\\AIAgent\\';
    }

    public static function initListenerSelf(): ModuleManagerListener
    {
        $classLoader = new \OpenEMR\Core\ModulesClassLoader($GLOBALS['fileroot']);
        $classLoader->registerNamespaceIfNotExists(
            'OpenEMR\\Modules\\AIAgent\\',
            __DIR__ . DIRECTORY_SEPARATOR . 'src'
        );
        return new self();
    }
}
