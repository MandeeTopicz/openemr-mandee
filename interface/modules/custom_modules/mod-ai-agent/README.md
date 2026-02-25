# CareTopicz AI Agent Module

OpenEMR module that embeds the CareTopicz AI assistant (Python FastAPI agent service).

## Requirements

- OpenEMR 7.0+
- CareTopicz agent service running (default: http://localhost:8000)

## Installation

1. **Register the module** in OpenEMR: Admin → Modules → Register
2. **Enable** the module
3. **Start the agent service** from the `agent-service/` directory:
   ```bash
   cd agent-service && uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Configuration

Optional globals (Administration → Config):

- `ai_agent_base_url` – Agent service URL (default: http://localhost:8000)
- `ai_agent_enabled` – Set to 0 to disable the chat widget

## Usage

A floating chat button appears on the patient dashboard and main pages. Click to open the chat panel and ask about drug interactions, symptoms, providers, appointments, or insurance.

## Troubleshooting (widget not showing on deployed instance)

If the widget works locally but not on a deployed server (e.g. GCP):

1. **Module registered and active**  
   OpenEMR only loads custom modules that have a row in the `modules` table with `mod_active = 1` and `type = 0`.  
   Run the verification/enable SQL:
   ```bash
   mysql -u openemr -p openemr < interface/modules/custom_modules/mod-ai-agent/sql/verify_and_enable_module.sql
   ```
   Or run the statements in phpMyAdmin. The script prints current status, runs `UPDATE ... SET mod_active = 1` for `mod-ai-agent`, and inserts the row if missing.

2. **Bootstrap and event listener**  
   The module is bootstrapped from `openemr.bootstrap.php`, which registers a listener for `PageHeadingRenderEvent`. The widget is injected only when `page_id` is one of: `core.mrd`, `core.main`, `patient-portal`, or `unknown` (patient dashboard / summary pages that don’t set a specific page_id). If your page uses a different `page_id`, add it in `src/Bootstrap.php` in the `$allowedPageIds` array.

3. **Chat widget HTML/JS**  
   The widget is rendered by `ChatWidgetController::renderFloatingButton()` and appended via `PageHeadingRenderEvent::appendTitleNavContent()`. If the widget still doesn’t appear after enabling the module, check that the page uses `OemrUI` and dispatches `PageHeadingRenderEvent` (patient chart and main content pages do).

4. **PHP error log**  
   Check the OpenEMR/PHP error log for module-related errors, e.g.:
   ```bash
   tail -f /var/log/php_errors.log
   # or Docker:
   docker compose exec openemr tail -f /var/log/apache2/error.log
   ```
   The Bootstrap logs "AIAgent: PageHeadingRenderEvent fired" and either "Appended chat widget" or "Skipping - page_id not matched" at error level to aid debugging.
