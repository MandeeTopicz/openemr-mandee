# GPL-2.0 Compatibility — CareTopicz Module

The CareTopicz OpenEMR module (`interface/modules/custom_modules/mod-ai-agent`) is structured to be compatible with GPL-2.0 as required for OpenEMR upstream.

## Module Code

- All PHP and JavaScript in the module is original or appropriately licensed.
- File headers reference the project license (GPL); the module directory includes a [LICENSE](../interface/modules/custom_modules/mod-ai-agent/LICENSE) file stating GPL-2.0 (or later).

## Dependencies

- **PHP:** The module uses GuzzleHttp (Composer dependency of OpenEMR). Guzzle is MIT-licensed, which is compatible with GPL-2.0 for use in a GPL-2.0 project.
- **JavaScript:** The chat widget uses vanilla JS and does not introduce new npm dependencies in the module; it relies on OpenEMR’s existing stack.
- **Agent service:** The Python agent service runs as a separate process and is not linked with the PHP module; it is not a derived work of the module for copyright purposes. The module only communicates with it over HTTP.

## Conclusion

The module is GPL-2.0 compatible. No incompatible dependencies or code have been identified. The LICENSE file in the module directory confirms GPL-2.0.
