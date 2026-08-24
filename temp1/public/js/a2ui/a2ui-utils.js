/* ═══════════════════════════════════════════════════════════════
   GEAP — A2UI pure utilities   (public/js/a2ui/a2ui-utils.js)

   Framework-free, DOM-free helpers shared between the Lit
   renderer (a2ui-view.js) and the unit test suite.  Exported as a
   UMD bundle so it works both as a browser ES-module import and as
   a CommonJS require() inside Node.js tests.

   Exports:
     reduceEnvelope(envelope)         → { rootId, components }
     encodePayload(envelope)          → base64 string
     decodePayload(base64)            → envelope object
     CATALOG_TYPES                    → string[] of all 12 catalog type names

   Catalog source of truth: geap-agent/app/a2ui/catalog.py.
   ═══════════════════════════════════════════════════════════════ */

(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory();
  } else if (typeof define === 'function' && define.amd) {
    define(factory);
  } else {
    root.A2uiUtils = factory();
  }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // All component types defined in the catalog.  Must stay in sync with
  // COMPONENT_TYPES in geap-agent/app/a2ui/catalog.py and with the
  // TYPE_RENDERERS map in a2ui-view.js.
  const CATALOG_TYPES = [
    'surface',
    'hero_cta',
    'stat_grid',
    'stat_tile',
    'tool_grid',
    'tool_card',
    'safeguard_panel',
    'safeguard_row',
    'chart_tabs',
    'glide_path_chart',
    'monte_carlo_chart',
    'allocation_chart'
  ];

  // ── Base64 helpers ────────────────────────────────────────────────────────

  function bytesToBase64(bytes) {
    let binary = '';
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
    }
    return btoa(binary);
  }

  function base64ToBytes(encoded) {
    const binary = atob(encoded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  // ── Envelope reducer ─────────────────────────────────────────────────────

  // Folds an envelope's messages into a flat { rootId, components } map.
  function reduceEnvelope(envelope) {
    let rootId = null;
    let components = {};

    for (const message of envelope.messages || []) {
      if (message.type === 'createSurface') {
        rootId = message.root || 'root';
      } else if (message.type === 'updateComponents') {
        for (const component of message.components || []) {
          components[component.id] = component;
        }
      } else if (message.type === 'deleteSurface') {
        rootId = null;
        components = {};
      }
      // updateDataModel: data is baked into props server-side; nothing to bind.
    }

    return { rootId, components };
  }

  // ── Payload encode / decode ───────────────────────────────────────────────

  // Base64-encodes a payload for safe transport as an HTML attribute value.
  // Uses TextEncoder for a correct, standards-compliant UTF-8 → Base64 path.
  function encodePayload(payload) {
    const json = JSON.stringify(payload);
    if (typeof TextEncoder !== 'undefined') {
      return bytesToBase64(new TextEncoder().encode(json));
    }
    if (typeof Buffer !== 'undefined') {
      return Buffer.from(json, 'utf8').toString('base64');
    }
    throw new Error('[a2ui-utils] missing TextEncoder support for payload encoding');
  }

  function decodePayload(encoded) {
    if (typeof TextDecoder !== 'undefined') {
      return JSON.parse(new TextDecoder().decode(base64ToBytes(encoded)));
    }
    if (typeof Buffer !== 'undefined') {
      return JSON.parse(Buffer.from(encoded, 'base64').toString('utf8'));
    }
    throw new Error('[a2ui-utils] missing TextDecoder support for payload decoding');
  }

  return { CATALOG_TYPES, reduceEnvelope, encodePayload, decodePayload };
}));
