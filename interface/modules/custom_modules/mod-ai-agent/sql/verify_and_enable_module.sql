-- CareTopicz AI Agent: verify module status and force-enable for GCP/deployed instances.
-- Run against your OpenEMR database (e.g. mysql openemr < verify_and_enable_module.sql or via phpMyAdmin).
--
-- 1) Check current status (module must exist and have mod_active = 1, type = 0 for custom)
SELECT mod_id, mod_name, mod_directory, mod_active, type, mod_ui_active, date
  FROM modules
 WHERE mod_directory = 'mod-ai-agent';

-- 2) Force-enable if the module row exists
UPDATE modules
   SET mod_active = 1,
       mod_ui_active = 1
 WHERE mod_directory = 'mod-ai-agent';

-- 3) If the module was never registered, insert it (custom module: type = 0).
--    Run only if step 1 returned no rows. Uses mod_id 9999 to avoid conflicting with existing IDs.
INSERT INTO modules (
    mod_id, mod_name, mod_directory, mod_parent, mod_type, mod_active,
    mod_ui_name, mod_relative_link, mod_ui_order, mod_ui_active, mod_description,
    mod_nick_name, mod_enc_menu, permissions_item_table, directory, date,
    sql_run, type, sql_version, acl_version
)
SELECT 9999, 'CareTopicz AI Agent', 'mod-ai-agent', '', '', 1,
       'CareTopicz AI Agent', 'index.php', 0, 1, 'AI chat widget on patient dashboard',
       'AI Agent', 'no', NULL, '', NOW(),
       1, 0, '0', '0'
 FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM modules WHERE mod_directory = 'mod-ai-agent');

-- 4) Verify after fix
SELECT mod_id, mod_name, mod_directory, mod_active, type
  FROM modules
 WHERE mod_directory = 'mod-ai-agent';
