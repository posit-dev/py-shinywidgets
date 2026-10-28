/* imjoy-rpc <-> Shiny bridge (experimental, for itkwidgets 1.0a).
 *
 * Mirrors imjoy-jupyterlab-extension/src/comm-connection.js but with Shiny
 * custom messages / inputs as the transport instead of a Jupyter comm.
 * Binary message parts travel base64-encoded since Shiny's websocket is
 * text-only.
 */
(function () {
  "use strict";

  // --- base64 <-> ArrayBuffer helpers -------------------------------------
  function b64encode(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
    }
    return btoa(binary);
  }
  function b64decode(b64) {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  }

  // --- buffer extraction (from imjoy-jupyterlab-extension) ----------------
  function isSerializable(object) {
    return typeof object === "object" && object && object.toJSON;
  }
  function isObject(value) {
    return value && typeof value === "object" && value.constructor === Object;
  }
  function putBuffers(state, bufferPaths, buffers) {
    buffers = buffers.map((b) => (b instanceof ArrayBuffer ? b : b.buffer));
    for (let i = 0; i < bufferPaths.length; i++) {
      const bufferPath = bufferPaths[i];
      let obj = state;
      for (let j = 0; j < bufferPath.length - 1; j++) {
        obj = obj[bufferPath[j]];
      }
      obj[bufferPath[bufferPath.length - 1]] = buffers[i];
    }
  }
  function removeBuffers(state) {
    const buffers = [];
    const bufferPaths = [];
    function remove(obj, path) {
      if (isSerializable(obj)) obj = obj.toJSON();
      if (Array.isArray(obj)) {
        let isCloned = false;
        for (let i = 0; i < obj.length; i++) {
          const value = obj[i];
          if (value) {
            if (value instanceof ArrayBuffer || ArrayBuffer.isView(value)) {
              if (!isCloned) {
                obj = obj.slice();
                isCloned = true;
              }
              buffers.push(ArrayBuffer.isView(value) ? value.buffer : value);
              bufferPaths.push(path.concat([i]));
              obj[i] = null;
            } else {
              const newValue = remove(value, path.concat([i]));
              if (newValue !== value) {
                if (!isCloned) {
                  obj = obj.slice();
                  isCloned = true;
                }
                obj[i] = newValue;
              }
            }
          }
        }
      } else if (isObject(obj)) {
        for (const key of Object.keys(obj)) {
          let isCloned = false;
          if (Object.prototype.hasOwnProperty.call(obj, key)) {
            const value = obj[key];
            if (value) {
              if (value instanceof ArrayBuffer || ArrayBuffer.isView(value)) {
                if (!isCloned) {
                  obj = { ...obj };
                  isCloned = true;
                }
                buffers.push(ArrayBuffer.isView(value) ? value.buffer : value);
                bufferPaths.push(path.concat([key]));
                delete obj[key];
              } else {
                const newValue = remove(value, path.concat([key]));
                if (newValue !== value) {
                  if (!isCloned) {
                    obj = { ...obj };
                    isCloned = true;
                  }
                  obj[key] = newValue;
                }
              }
            }
          }
        }
      }
      return obj;
    }
    const newState = remove(state, []);
    return { state: newState, buffers, buffer_paths: bufferPaths };
  }

  // --- MessageEmitter ------------------------------------------------------
  class MessageEmitter {
    constructor() {
      this._event_handlers = {};
    }
    on(event, handler) {
      (this._event_handlers[event] = this._event_handlers[event] || []).push(
        handler
      );
    }
    once(event, handler) {
      handler.___event_run_once = true;
      this.on(event, handler);
    }
    off(event, handler) {
      if (!event && !handler) this._event_handlers = {};
      else if (event && !handler) this._event_handlers[event] = [];
      else if (this._event_handlers[event]) {
        const idx = this._event_handlers[event].indexOf(handler);
        if (idx >= 0) this._event_handlers[event].splice(idx, 1);
      }
    }
    _fire(event, data) {
      if (this._event_handlers[event]) {
        let i = this._event_handlers[event].length;
        while (i--) {
          const handler = this._event_handlers[event][i];
          try {
            handler(data);
          } catch (e) {
            console.error(e);
          } finally {
            if (handler.___event_run_once) {
              this._event_handlers[event].splice(i, 1);
            }
          }
        }
      }
    }
  }

  // --- Connection over Shiny messages --------------------------------------
  const connections = {};

  class ShinyImjoyConnection extends MessageEmitter {
    constructor(connectionId) {
      super();
      this.connectionId = connectionId;
      this._peer_id = null;
      connections[connectionId] = this;
    }
    connect() {
      // Tell Python we're ready for the imjoyRPCReady handshake message
      this._sendRaw({ type: "browserReady" });
    }
    disconnect() {
      delete connections[this.connectionId];
    }
    _sendRaw(data) {
      Shiny.setInputValue(
        "imjoy_rpc_send",
        JSON.stringify({
          connection_id: this.connectionId,
          container_id: this.containerId || "",
          export_id: this.exportId || null,
          data: data,
          buffers: [],
        }),
        { priority: "event" }
      );
    }
    emit(data) {
      data.peer_id = this._peer_id;
      const split = removeBuffers(data);
      split.state.__buffer_paths__ = split.buffer_paths;
      Shiny.setInputValue(
        "imjoy_rpc_send",
        JSON.stringify({
          connection_id: this.connectionId,
          data: split.state,
          buffers: split.buffers.map(b64encode),
        }),
        { priority: "event" }
      );
    }
    _receive(data, buffers) {
      const bufferPaths = data.__buffer_paths__ || [];
      delete data.__buffer_paths__;
      putBuffers(data, bufferPaths, buffers.map(b64decode));
      if (data.type === "log" || data.type === "info") {
        console.log("[imjoy]", data.message);
      } else if (data.type === "error") {
        console.error("[imjoy]", data.message);
      } else {
        if (data.peer_id) this._peer_id = data.peer_id;
        this._fire(data.type, data);
      }
    }
  }

  // --- imjoy core bootstrap ------------------------------------------------
  let imjoyApp = null;
  async function getImjoy() {
    if (imjoyApp) return imjoyApp;
    const app = await imjoyLoader.loadImJoyBasicApp({
      process_url_query: false,
      show_window_title: false,
      show_progress_bar: false,
      show_empty_window: false,
      menu_style: { position: "absolute", right: 0, top: "2px" },
      window_style: { width: "100%", height: "100%" },
      main_container: null,
      menu_container: null,
      expose_api: false,
      imjoy_api: {
        async createWindow(_plugin, w, extra_config) {
          // Root-relative viewer URLs (e.g. self-hosted static assets) need
          // an absolute origin for imjoy's window-spec validation
          if (w.src && w.src.startsWith("/")) w.src = location.origin + w.src;
          // Mount inline inside the container named by the Python side
          if (!document.getElementById(w.window_id)) {
            const container =
              (w._container_id && document.getElementById(w._container_id)) ||
              null;
            const elem = document.createElement("div");
            elem.id = w.window_id;
            elem.classList.add("imjoy-inline-window");
            elem.style.width = "100%";
            elem.style.height = "100%";
            (container || document.body).appendChild(elem);
          }
          return await app.imjoy.pm.createWindow(_plugin, w, extra_config);
        },
      },
    });
    imjoyApp = app;
    window._imjoyApp = app; // useful for debugging
    return app;
  }

  // --- Shiny message handlers ----------------------------------------------
  // NOTE: this handler must return immediately (no top-level await): Shiny
  // serializes custom-message dispatch, so awaiting connectPlugin here blocks
  // delivery of subsequent imjoy_rpc_msg frames (observed: messages stalled
  // for exactly the 15 s connectPlugin timeout).
  Shiny.addCustomMessageHandler("imjoy_connect", function (msg) {
    const { connection_id, container_id, export_id } = JSON.parse(msg);
    (async () => {
      const app = await getImjoy();
      const conn = new ShinyImjoyConnection(connection_id);
      conn.containerId = container_id;
      conn.exportId = export_id;
      const plugin = await app.imjoy.pm.connectPlugin(conn);
      if (plugin && plugin.api && plugin.api.run) {
        await plugin.api.run({ config: {}, data: {} });
      }
    })().catch((e) => console.error("[imjoy-bridge] connectPlugin failed", e));
  });

  Shiny.addCustomMessageHandler("imjoy_rpc_msg", function (msg) {
    const { connection_id, data, buffers } = JSON.parse(msg);
    const conn = connections[connection_id];
    if (!conn) {
      console.warn("[imjoy-bridge] no connection", connection_id);
      return;
    }
    conn._receive(data, buffers || []);
  });
})();
