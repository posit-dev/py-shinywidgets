/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
require(["@jupyter-widgets/html-manager"], (__WEBPACK_EXTERNAL_MODULE__jupyter_widgets_html_manager__) => { return /******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./node_modules/base64-arraybuffer/dist/base64-arraybuffer.es5.js":
/*!************************************************************************!*\
  !*** ./node_modules/base64-arraybuffer/dist/base64-arraybuffer.es5.js ***!
  \************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"decode\": () => (/* binding */ decode),\n/* harmony export */   \"encode\": () => (/* binding */ encode)\n/* harmony export */ });\n/*\n * base64-arraybuffer 1.0.2 <https://github.com/niklasvh/base64-arraybuffer>\n * Copyright (c) 2022 Niklas von Hertzen <https://hertzen.com>\n * Released under MIT License\n */\nvar chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';\n// Use a lookup table to find the index.\nvar lookup = typeof Uint8Array === 'undefined' ? [] : new Uint8Array(256);\nfor (var i = 0; i < chars.length; i++) {\n    lookup[chars.charCodeAt(i)] = i;\n}\nvar encode = function (arraybuffer) {\n    var bytes = new Uint8Array(arraybuffer), i, len = bytes.length, base64 = '';\n    for (i = 0; i < len; i += 3) {\n        base64 += chars[bytes[i] >> 2];\n        base64 += chars[((bytes[i] & 3) << 4) | (bytes[i + 1] >> 4)];\n        base64 += chars[((bytes[i + 1] & 15) << 2) | (bytes[i + 2] >> 6)];\n        base64 += chars[bytes[i + 2] & 63];\n    }\n    if (len % 3 === 2) {\n        base64 = base64.substring(0, base64.length - 1) + '=';\n    }\n    else if (len % 3 === 1) {\n        base64 = base64.substring(0, base64.length - 2) + '==';\n    }\n    return base64;\n};\nvar decode = function (base64) {\n    var bufferLength = base64.length * 0.75, len = base64.length, i, p = 0, encoded1, encoded2, encoded3, encoded4;\n    if (base64[base64.length - 1] === '=') {\n        bufferLength--;\n        if (base64[base64.length - 2] === '=') {\n            bufferLength--;\n        }\n    }\n    var arraybuffer = new ArrayBuffer(bufferLength), bytes = new Uint8Array(arraybuffer);\n    for (i = 0; i < len; i += 4) {\n        encoded1 = lookup[base64.charCodeAt(i)];\n        encoded2 = lookup[base64.charCodeAt(i + 1)];\n        encoded3 = lookup[base64.charCodeAt(i + 2)];\n        encoded4 = lookup[base64.charCodeAt(i + 3)];\n        bytes[p++] = (encoded1 << 2) | (encoded2 >> 4);\n        bytes[p++] = ((encoded2 & 15) << 4) | (encoded3 >> 2);\n        bytes[p++] = ((encoded3 & 3) << 6) | (encoded4 & 63);\n    }\n    return arraybuffer;\n};\n\n\n//# sourceMappingURL=base64-arraybuffer.es5.js.map\n\n\n//# sourceURL=webpack://@jupyter-widgets/prism-embed-manager/./node_modules/base64-arraybuffer/dist/base64-arraybuffer.es5.js?");

/***/ }),

/***/ "./src/comm.ts":
/*!*********************!*\
  !*** ./src/comm.ts ***!
  \*********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"ShinyComm\": () => (/* binding */ ShinyComm)\n/* harmony export */ });\n// This class is a striped down version of Comm from @jupyter-widgets/base\n// https://github.com/jupyter-widgets/ipywidgets/blob/88cec8/packages/base/src/services-shim.ts#L192-L335\n// Note that the Kernel.IComm implementation is located here\n// https://github.com/jupyterlab/jupyterlab/blob/master/packages/services/src/kernel/comm.ts\nclass ShinyComm {\n    constructor(model_id) {\n        this.comm_id = model_id;\n    }\n    // This might not be needed\n    get target_name() {\n        return \"jupyter.widgets\";\n    }\n    send(data, callbacks, metadata, buffers) {\n        const msg = {\n            content: { comm_id: this.comm_id, data: data },\n            metadata: metadata,\n            buffers: buffers || [],\n            // this doesn't seem relevant to the widget?\n            header: {}\n        };\n        const msg_txt = JSON.stringify(msg);\n        Shiny.setInputValue(\"shinywidgets_comm_send\", msg_txt, { priority: \"event\" });\n        // When client-side changes happen to the WidgetModel, this send method\n        // won't get called for _every_  change (just the first one). The\n        // expectation is that this method will eventually end up calling itself\n        // (via callbacks) when the server is ready (i.e., idle) to receive more\n        // updates. To make sense of this, see\n        // https://github.com/jupyter-widgets/ipywidgets/blob/88cec8b/packages/base/src/widget.ts#L550-L557\n        if (callbacks && callbacks.iopub && callbacks.iopub.status) {\n            setTimeout(() => {\n                // TODO: Call this when Shiny reports that it is idle?\n                const msg = { content: { execution_state: \"idle\" } };\n                callbacks.iopub.status(msg);\n            }, 0);\n        }\n        return this.comm_id;\n    }\n    open(data, callbacks, metadata, buffers) {\n        // I don't think we need to do anything here?\n        return this.comm_id;\n    }\n    close(data, callbacks, metadata, buffers) {\n        // I don't think we need to do anything here?\n        return this.comm_id;\n    }\n    on_msg(callback) {\n        this._msg_callback = callback.bind(this);\n    }\n    on_close(callback) {\n        this._close_callback = callback.bind(this);\n    }\n    handle_msg(msg) {\n        if (this._msg_callback)\n            this._msg_callback(msg);\n    }\n    handle_close(msg) {\n        if (this._close_callback)\n            this._close_callback(msg);\n    }\n}\n\n\n//# sourceURL=webpack://@jupyter-widgets/prism-embed-manager/./src/comm.ts?");

/***/ }),

/***/ "./src/output.ts":
/*!***********************!*\
  !*** ./src/output.ts ***!
  \***********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @jupyter-widgets/html-manager */ \"@jupyter-widgets/html-manager\");\n/* harmony import */ var _jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _comm__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./comm */ \"./src/comm.ts\");\n/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./utils */ \"./src/utils.ts\");\n\n\n\n/******************************************************************************\n * Define a custom HTMLManager for use with Shiny\n ******************************************************************************/\nclass OutputManager extends _jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__.HTMLManager {\n    // In a soon-to-be-released version of @jupyter-widgets/html-manager,\n    // display_view()'s first \"dummy\" argument will be removed... this shim simply\n    // makes it so that our manager can work with either version\n    // https://github.com/jupyter-widgets/ipywidgets/commit/159bbe4#diff-45c126b24c3c43d2cee5313364805c025e911c4721d45ff8a68356a215bfb6c8R42-R43\n    async display_view(view, options) {\n        const n_args = super.display_view.length;\n        if (n_args === 3) {\n            return super.display_view({}, view, options);\n        }\n        else {\n            // @ts-ignore\n            return super.display_view(view, options);\n        }\n    }\n}\n// Define our own custom module loader for Shiny\nconst shinyRequireLoader = async function (moduleName, moduleVersion) {\n    // shiny provides require.js and also sets `define.amd=false` to prevent <script>s\n    // with UMD loaders from triggering anonymous define() errors. shinywidgets should\n    // generally be able to avoid anonymous define errors though since there should only\n    // be one 'main' anonymous define() for the widget's module (located in a JS file that\n    // we've already require.config({paths: {...}})ed; and in that case, requirejs adds a\n    // data-requiremodule attribute to the <script> tag that shiny's custom define will\n    // recognize and use as the name).)\n    const oldAmd = window.define.amd;\n    // The is the original value for define.amd that require.js sets\n    window.define.amd = { jQuery: true };\n    // Store jQuery global since loading we load a module, it may overwrite it\n    // (qgrid is one good example)\n    const old$ = window.$;\n    const oldJQ = window.jQuery;\n    if (moduleName === 'qgrid') {\n        // qgrid wants to use base/js/dialog (if it's available) for full-screen tables\n        // https://github.com/quantopian/qgrid/blob/877b420/js/src/qgrid.widget.js#L11-L16\n        // Maybe that's worth supporting someday, but for now, we define it to be nothing\n        // to avoid require('qgrid') from producing an error\n        window.define(\"base/js/dialog\", [], function () { return null; });\n    }\n    return (0,_jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__.requireLoader)(moduleName, moduleVersion).finally(() => {\n        window.define.amd = oldAmd;\n        window.$ = old$;\n        window.jQuery = oldJQ;\n    });\n};\nconst manager = new OutputManager({ loader: shinyRequireLoader });\n/******************************************************************************\n* Define the Shiny binding\n******************************************************************************/\n// Ideally we'd extend Shiny's HTMLOutputBinding, but the implementation isn't exported\nclass IPyWidgetOutput extends Shiny.OutputBinding {\n    find(scope) {\n        return $(scope).find(\".shiny-ipywidget-output\");\n    }\n    onValueError(el, err) {\n        Shiny.unbindAll(el);\n        this.renderError(el, err);\n    }\n    renderValue(el, data) {\n        // Allow for a None/null value to hide the widget (css inspired by htmlwidgets)\n        if (!data) {\n            el.style.visibility = \"hidden\";\n            return;\n        }\n        else {\n            el.style.visibility = \"inherit\";\n        }\n        // At this time point, we should've already handled an 'open' message, and so\n        // the model should be ready to use\n        const model = manager.get_model(data.model_id);\n        if (!model) {\n            throw new Error(`No model found for id ${data.model_id}`);\n        }\n        model.then((m) => {\n            const view = manager.create_view(m, {});\n            view.then(v => {\n                manager.display_view(v, { el: el }).then(() => {\n                    // TODO: It would be better to .close() the widget here, but\n                    // I'm not sure how to do that yet (at least client-side)\n                    while (el.childNodes.length > 1) {\n                        el.removeChild(el.childNodes[0]);\n                    }\n                });\n            });\n        });\n    }\n}\nShiny.outputBindings.register(new IPyWidgetOutput(), \"shiny.IPyWidgetOutput\");\n/******************************************************************************\n* Handle messages from the server-side Widget\n******************************************************************************/\n// Initialize the comm and model when a new widget is created\n// This is basically our version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1144-L1176\nShiny.addCustomMessageHandler(\"shinywidgets_comm_open\", (msg_txt) => {\n    setBaseURL();\n    const msg = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.jsonParse)(msg_txt);\n    Shiny.renderDependencies(msg.content.html_deps);\n    const comm = new _comm__WEBPACK_IMPORTED_MODULE_1__.ShinyComm(msg.content.comm_id);\n    manager.handle_comm_open(comm, msg);\n});\n// Handle any mutation of the model (e.g., add a marker to a map, without a full redraw)\n// Basically out version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1200-L1215\nShiny.addCustomMessageHandler(\"shinywidgets_comm_msg\", (msg_txt) => {\n    const msg = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.jsonParse)(msg_txt);\n    manager.get_model(msg.content.comm_id).then(m => {\n        // @ts-ignore for some reason IClassicComm doesn't have this method, but we do\n        m.comm.handle_msg(msg);\n    });\n});\n// TODO: test that this actually works\nShiny.addCustomMessageHandler(\"shinywidgets_comm_close\", (msg_txt) => {\n    const msg = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.jsonParse)(msg_txt);\n    manager.get_model(msg.content.comm_id).then(m => {\n        // @ts-ignore for some reason IClassicComm doesn't have this method, but we do\n        m.comm.handle_close(msg);\n    });\n});\n// Our version of https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8\nfunction setBaseURL(x = '') {\n    const base_url = document.querySelector('body').getAttribute('data-base-url');\n    if (!base_url) {\n        document.querySelector('body').setAttribute('data-base-url', x);\n    }\n}\n\n\n//# sourceURL=webpack://@jupyter-widgets/prism-embed-manager/./src/output.ts?");

/***/ }),

/***/ "./src/utils.ts":
/*!**********************!*\
  !*** ./src/utils.ts ***!
  \**********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"jsonParse\": () => (/* binding */ jsonParse)\n/* harmony export */ });\n/* harmony import */ var base64_arraybuffer__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! base64-arraybuffer */ \"./node_modules/base64-arraybuffer/dist/base64-arraybuffer.es5.js\");\n\n// On the server, we're using jupyter_client.session.json_packer to serialize messages,\n// and it encodes binary data (i.e., buffers) as base64, so decode it before passing it\n// along to the comm logic\nfunction jsonParse(x) {\n    const msg = JSON.parse(x);\n    msg.buffers = msg.buffers.map((b) => (0,base64_arraybuffer__WEBPACK_IMPORTED_MODULE_0__.decode)(b));\n    return msg;\n}\n\n\n//# sourceURL=webpack://@jupyter-widgets/prism-embed-manager/./src/utils.ts?");

/***/ }),

/***/ "@jupyter-widgets/html-manager":
/*!************************************************!*\
  !*** external "@jupyter-widgets/html-manager" ***!
  \************************************************/
/***/ ((module) => {

module.exports = __WEBPACK_EXTERNAL_MODULE__jupyter_widgets_html_manager__;

/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/compat get default export */
/******/ 	(() => {
/******/ 		// getDefaultExport function for compatibility with non-harmony modules
/******/ 		__webpack_require__.n = (module) => {
/******/ 			var getter = module && module.__esModule ?
/******/ 				() => (module['default']) :
/******/ 				() => (module);
/******/ 			__webpack_require__.d(getter, { a: getter });
/******/ 			return getter;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module can't be inlined because the eval devtool is used.
/******/ 	var __webpack_exports__ = __webpack_require__("./src/output.ts");
/******/ 	
/******/ 	return __webpack_exports__;
/******/ })()
;
});;