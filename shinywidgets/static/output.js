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

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"decode\": () => (/* binding */ decode),\n/* harmony export */   \"encode\": () => (/* binding */ encode)\n/* harmony export */ });\n/*\n * base64-arraybuffer 1.0.2 <https://github.com/niklasvh/base64-arraybuffer>\n * Copyright (c) 2022 Niklas von Hertzen <https://hertzen.com>\n * Released under MIT License\n */\nvar chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';\n// Use a lookup table to find the index.\nvar lookup = typeof Uint8Array === 'undefined' ? [] : new Uint8Array(256);\nfor (var i = 0; i < chars.length; i++) {\n    lookup[chars.charCodeAt(i)] = i;\n}\nvar encode = function (arraybuffer) {\n    var bytes = new Uint8Array(arraybuffer), i, len = bytes.length, base64 = '';\n    for (i = 0; i < len; i += 3) {\n        base64 += chars[bytes[i] >> 2];\n        base64 += chars[((bytes[i] & 3) << 4) | (bytes[i + 1] >> 4)];\n        base64 += chars[((bytes[i + 1] & 15) << 2) | (bytes[i + 2] >> 6)];\n        base64 += chars[bytes[i + 2] & 63];\n    }\n    if (len % 3 === 2) {\n        base64 = base64.substring(0, base64.length - 1) + '=';\n    }\n    else if (len % 3 === 1) {\n        base64 = base64.substring(0, base64.length - 2) + '==';\n    }\n    return base64;\n};\nvar decode = function (base64) {\n    var bufferLength = base64.length * 0.75, len = base64.length, i, p = 0, encoded1, encoded2, encoded3, encoded4;\n    if (base64[base64.length - 1] === '=') {\n        bufferLength--;\n        if (base64[base64.length - 2] === '=') {\n            bufferLength--;\n        }\n    }\n    var arraybuffer = new ArrayBuffer(bufferLength), bytes = new Uint8Array(arraybuffer);\n    for (i = 0; i < len; i += 4) {\n        encoded1 = lookup[base64.charCodeAt(i)];\n        encoded2 = lookup[base64.charCodeAt(i + 1)];\n        encoded3 = lookup[base64.charCodeAt(i + 2)];\n        encoded4 = lookup[base64.charCodeAt(i + 3)];\n        bytes[p++] = (encoded1 << 2) | (encoded2 >> 4);\n        bytes[p++] = ((encoded2 & 15) << 4) | (encoded3 >> 2);\n        bytes[p++] = ((encoded3 & 3) << 6) | (encoded4 & 63);\n    }\n    return arraybuffer;\n};\n\n\n//# sourceMappingURL=base64-arraybuffer.es5.js.map\n\n\n//# sourceURL=webpack://@jupyter-widgets/shiny-embed-manager/./node_modules/base64-arraybuffer/dist/base64-arraybuffer.es5.js?");

/***/ }),

/***/ "./src/comm.ts":
/*!*********************!*\
  !*** ./src/comm.ts ***!
  \*********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"ShinyComm\": () => (/* binding */ ShinyComm)\n/* harmony export */ });\n/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./utils */ \"./src/utils.ts\");\n\n// This class is a striped down version of Comm from @jupyter-widgets/base\n// https://github.com/jupyter-widgets/ipywidgets/blob/88cec8/packages/base/src/services-shim.ts#L192-L335\n// Note that the Kernel.IComm implementation is located here\n// https://github.com/jupyterlab/jupyterlab/blob/master/packages/services/src/kernel/comm.ts\nclass ShinyComm {\n    constructor(model_id) {\n        this.comm_id = model_id;\n        // TODO: make this configurable (see comments in send() below)?\n        this.throttler = new _utils__WEBPACK_IMPORTED_MODULE_0__.Throttler(100);\n    }\n    // This might not be needed\n    get target_name() {\n        return \"jupyter.widgets\";\n    }\n    send(data, callbacks, metadata, buffers) {\n        const msg = {\n            content: { comm_id: this.comm_id, data: data },\n            metadata: metadata,\n            // TODO: need to _encode_ any buffers into base64 (JSON.stringify just drops them)\n            buffers: buffers || [],\n            // this doesn't seem relevant to the widget?\n            header: {}\n        };\n        const msg_txt = JSON.stringify(msg);\n        // Since ipyleaflet can send mousemove events very quickly when hovering over the map,\n        // we throttle them to ensure that the server doesn't get overwhelmed. Said events\n        // generate a payload that looks like this:\n        // {\"method\": \"custom\", \"content\": {\"event\": \"interaction\", \"type\": \"mousemove\", \"coordinates\": [-17.76259815404015, 12.096729340756617]}}\n        //\n        // TODO: This is definitely not ideal. It would be better to have a way to specify/\n        // customize throttle rates instead of having such a targetted fix for ipyleaflet.\n        const is_mousemove = data.method === \"custom\" &&\n            data.content.event === \"interaction\" &&\n            data.content.type === \"mousemove\";\n        if (is_mousemove) {\n            this.throttler.throttle(() => {\n                Shiny.setInputValue(\"shinywidgets_comm_send\", msg_txt, { priority: \"event\" });\n            });\n        }\n        else {\n            this.throttler.flush();\n            Shiny.setInputValue(\"shinywidgets_comm_send\", msg_txt, { priority: \"event\" });\n        }\n        // When client-side changes happen to the WidgetModel, this send method\n        // won't get called for _every_  change (just the first one). The\n        // expectation is that this method will eventually end up calling itself\n        // (via callbacks) when the server is ready (i.e., idle) to receive more\n        // updates. To make sense of this, see\n        // https://github.com/jupyter-widgets/ipywidgets/blob/88cec8b/packages/base/src/widget.ts#L550-L557\n        if (callbacks && callbacks.iopub && callbacks.iopub.status) {\n            setTimeout(() => {\n                // TODO-future: it doesn't seem quite right to report that shiny is always idle.\n                // Maybe listen to the shiny-busy flag?\n                // const state = document.querySelector(\"html\").classList.contains(\"shiny-busy\") ? \"busy\" : \"idle\";\n                const msg = { content: { execution_state: \"idle\" } };\n                callbacks.iopub.status(msg);\n            }, 0);\n        }\n        return this.comm_id;\n    }\n    open(data, callbacks, metadata, buffers) {\n        // I don't think we need to do anything here?\n        return this.comm_id;\n    }\n    close(data, callbacks, metadata, buffers) {\n        // I don't think we need to do anything here?\n        return this.comm_id;\n    }\n    on_msg(callback) {\n        this._msg_callback = callback.bind(this);\n    }\n    on_close(callback) {\n        this._close_callback = callback.bind(this);\n    }\n    handle_msg(msg) {\n        if (this._msg_callback)\n            this._msg_callback(msg);\n    }\n    handle_close(msg) {\n        if (this._close_callback)\n            this._close_callback(msg);\n    }\n}\n\n\n//# sourceURL=webpack://@jupyter-widgets/shiny-embed-manager/./src/comm.ts?");

/***/ }),

/***/ "./src/output.ts":
/*!***********************!*\
  !*** ./src/output.ts ***!
  \***********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! @jupyter-widgets/html-manager */ \"@jupyter-widgets/html-manager\");\n/* harmony import */ var _jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _comm__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./comm */ \"./src/comm.ts\");\n/* harmony import */ var _utils__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./utils */ \"./src/utils.ts\");\nvar _a;\n\n\n\n/******************************************************************************\n * Define a custom HTMLManager for use with Shiny\n ******************************************************************************/\nclass OutputManager extends _jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__.HTMLManager {\n    // In a soon-to-be-released version of @jupyter-widgets/html-manager,\n    // display_view()'s first \"dummy\" argument will be removed... this shim simply\n    // makes it so that our manager can work with either version\n    // https://github.com/jupyter-widgets/ipywidgets/commit/159bbe4#diff-45c126b24c3c43d2cee5313364805c025e911c4721d45ff8a68356a215bfb6c8R42-R43\n    async display_view(view, options) {\n        const n_args = super.display_view.length;\n        if (n_args === 3) {\n            return super.display_view({}, view, options);\n        }\n        else {\n            // @ts-ignore\n            return super.display_view(view, options);\n        }\n    }\n}\n// Define our own custom module loader for Shiny\nconst shinyRequireLoader = async function (moduleName, moduleVersion) {\n    // shiny provides a shim of require.js which allows <script>s with anonymous\n    // define()s to be loaded without error. When an anonymous define() occurs,\n    // the shim uses the data-requiremodule attribute (set by require.js) on the script\n    // to determine the module name.\n    // https://github.com/posit-dev/py-shiny/blob/230940c/scripts/define-shims.js#L10-L16\n    // In the context of shinywidgets, when a widget gets rendered, it should\n    // come with another <script> tag that does `require.config({paths: {...}})`\n    // which maps the module name to a URL of the widget's JS file.\n    const oldAmd = window.define.amd;\n    // This is probably not necessary, but just in case -- especially now in a\n    // anywidget/ES6 world, we probably don't want to load AMD modules\n    // (plotly is one example of a widget that will fail to load if AMD is enabled)\n    window.define.amd = false;\n    // Store jQuery global since loading we load a module, it may overwrite it\n    // (qgrid is one good example)\n    const old$ = window.$;\n    const oldJQ = window.jQuery;\n    if (moduleName === 'qgrid') {\n        // qgrid wants to use base/js/dialog (if it's available) for full-screen tables\n        // https://github.com/quantopian/qgrid/blob/877b420/js/src/qgrid.widget.js#L11-L16\n        // Maybe that's worth supporting someday, but for now, we define it to be nothing\n        // to avoid require('qgrid') from producing an error\n        window.define(\"base/js/dialog\", [], function () { return null; });\n    }\n    return (0,_jupyter_widgets_html_manager__WEBPACK_IMPORTED_MODULE_0__.requireLoader)(moduleName, moduleVersion).finally(() => {\n        window.define.amd = oldAmd;\n        window.$ = old$;\n        window.jQuery = oldJQ;\n    });\n};\nconst manager = new OutputManager({ loader: shinyRequireLoader });\n/******************************************************************************\n* Define the Shiny binding\n******************************************************************************/\n// Ideally we'd extend Shiny's HTMLOutputBinding, but the implementation isn't exported\nclass IPyWidgetOutput extends Shiny.OutputBinding {\n    find(scope) {\n        return $(scope).find(\".shiny-ipywidget-output\");\n    }\n    onValueError(el, err) {\n        Shiny.unbindAll(el);\n        this.renderError(el, err);\n    }\n    async renderValue(el, data) {\n        // Allow for a None/null value to hide the widget (css inspired by htmlwidgets)\n        if (!data) {\n            el.style.visibility = \"hidden\";\n            return;\n        }\n        else {\n            el.style.visibility = \"inherit\";\n        }\n        // Only forward the potential to fill if `output_widget(fillable=True)`\n        // _and_ the widget instance wants to fill\n        const fill = data.fill && el.classList.contains(\"html-fill-container\");\n        if (fill)\n            el.classList.add(\"forward-fill-potential\");\n        // At this time point, we should've already handled an 'open' message, and so\n        // the model should be ready to use\n        const model = await manager.get_model(data.model_id);\n        if (!model) {\n            throw new Error(`No model found for id ${data.model_id}`);\n        }\n        const view = await manager.create_view(model, {});\n        await manager.display_view(view, { el: el });\n        // The ipywidgets container (.lmWidget)\n        const lmWidget = el.children[0];\n        if (fill) {\n            this._onImplementation(lmWidget, () => this._doAddFillClasses(lmWidget));\n        }\n        this._onImplementation(lmWidget, this._doResize);\n    }\n    _onImplementation(lmWidget, callback) {\n        if (this._hasImplementation(lmWidget)) {\n            callback();\n            return;\n        }\n        // Some widget implementation (e.g., ipyleaflet, pydeck) won't actually\n        // have rendered to the DOM at this point, so wait until they do\n        const mo = new MutationObserver((mutations) => {\n            if (this._hasImplementation(lmWidget)) {\n                mo.disconnect();\n                callback();\n            }\n        });\n        mo.observe(lmWidget, { childList: true });\n    }\n    // In most cases, we can get widgets to fill through Python/CSS, but some widgets\n    // (e.g., quak) don't have a Python API and use shadow DOM, which can only access\n    // from JS\n    _doAddFillClasses(lmWidget) {\n        var _a;\n        const impl = lmWidget.children[0];\n        const isQuakWidget = impl && !!((_a = impl.shadowRoot) === null || _a === void 0 ? void 0 : _a.querySelector(\".quak\"));\n        if (isQuakWidget) {\n            impl.classList.add(\"html-fill-container\", \"html-fill-item\");\n            const quakWidget = impl.shadowRoot.querySelector(\".quak\");\n            quakWidget.style.maxHeight = \"unset\";\n        }\n    }\n    _doResize() {\n        // Trigger resize event to force layout (setTimeout() is needed for altair)\n        // TODO: debounce this call?\n        setTimeout(() => {\n            window.dispatchEvent(new Event('resize'));\n        }, 0);\n    }\n    _hasImplementation(lmWidget) {\n        var _a;\n        const impl = lmWidget.children[0];\n        return impl && (impl.children.length > 0 || ((_a = impl.shadowRoot) === null || _a === void 0 ? void 0 : _a.children.length) > 0);\n    }\n}\nShiny.outputBindings.register(new IPyWidgetOutput(), \"shiny.IPyWidgetOutput\");\n// Due to the way HTMLManager (and widget implementations) get loaded (via\n// require.js), the binding registration above can happen _after_ Shiny has\n// already bound the DOM, especially in the dynamic UI case (i.e., output_binding()'s\n// dependencies don't come in until after initial page load). And, in the dynamic UI\n// case, UI is rendered asychronously via Shiny.shinyapp.taskQueue, so if it exists,\n// we probably need to re-bind the DOM after the taskQueue is done.\nconst taskQueue = (_a = Shiny === null || Shiny === void 0 ? void 0 : Shiny.shinyapp) === null || _a === void 0 ? void 0 : _a.taskQueue;\nif (taskQueue) {\n    taskQueue.enqueue(() => Shiny.bindAll(document.body));\n}\n/******************************************************************************\n* Handle messages from the server-side Widget\n******************************************************************************/\n// Initialize the comm and model when a new widget is created\n// This is basically our version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1144-L1176\nShiny.addCustomMessageHandler(\"shinywidgets_comm_open\", (msg_txt) => {\n    setBaseURL();\n    const msg = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.jsonParse)(msg_txt);\n    Shiny.renderDependencies(msg.content.html_deps);\n    const comm = new _comm__WEBPACK_IMPORTED_MODULE_1__.ShinyComm(msg.content.comm_id);\n    manager.handle_comm_open(comm, msg);\n});\n// Handle any mutation of the model (e.g., add a marker to a map, without a full redraw)\n// Basically out version of https://github.com/jupyterlab/jupyterlab/blob/d33de15/packages/services/src/kernel/default.ts#L1200-L1215\nShiny.addCustomMessageHandler(\"shinywidgets_comm_msg\", async (msg_txt) => {\n    const msg = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.jsonParse)(msg_txt);\n    const id = msg.content.comm_id;\n    const model = manager.get_model(id);\n    if (!model) {\n        console.error(`Couldn't handle message for model ${id} because it doesn't exist.`);\n        return;\n    }\n    try {\n        const m = await model;\n        // @ts-ignore for some reason IClassicComm doesn't have this method, but we do\n        m.comm.handle_msg(msg);\n    }\n    catch (err) {\n        console.error(\"Error handling message:\", err);\n    }\n});\n// Handle the closing of a widget/comm/model\nShiny.addCustomMessageHandler(\"shinywidgets_comm_close\", async (msg_txt) => {\n    const msg = (0,_utils__WEBPACK_IMPORTED_MODULE_2__.jsonParse)(msg_txt);\n    const id = msg.content.comm_id;\n    const model = manager.get_model(id);\n    if (!model) {\n        console.error(`Couldn't close model ${id} because it doesn't exist.`);\n        return;\n    }\n    try {\n        const m = await model;\n        // Before .close()ing the model (which will .remove() each view), do some\n        // additional cleanup that .remove() might miss\n        await Promise.all(Object.values(m.views).map(async (viewPromise) => {\n            try {\n                const v = await viewPromise;\n                // Old versions of plotly need a .destroy() to properly clean up\n                // https://github.com/plotly/plotly.py/pull/3805/files#diff-259c92d\n                if (hasMethod(v, 'destroy')) {\n                    v.destroy();\n                    // Also, empirically, when this destroy() is relevant, it also helps to\n                    // delete the view's reference to the model, I think this is the only\n                    // way to drop the resize event listener (see the diff in the link above)\n                    // https://github.com/posit-dev/py-shinywidgets/issues/166\n                    delete v.model;\n                    // Ensure sure the lm-Widget container is also removed\n                    v.remove();\n                }\n            }\n            catch (err) {\n                console.error(\"Error cleaning up view:\", err);\n            }\n        }));\n        // Close model after all views are cleaned up\n        await m.close();\n        // Trigger comm:close event to remove manager's reference\n        m.trigger(\"comm:close\");\n    }\n    catch (err) {\n        console.error(\"Error during model cleanup:\", err);\n    }\n});\n$(document).on(\"shiny:disconnected\", () => {\n    manager.clear_state();\n});\n// When in filling layout, some widgets (specifically, altair) incorrectly think their\n// height is 0 after it's shown, hidden, then shown again. As a workaround, trigger a\n// resize event when a tab is shown.\n// TODO: This covers the 95% use case, but it's definitely not an ideal way to handle\n// this situation. A more robust solution would use IntersectionObserver to detect when\n// the widget becomes visible. Or better yet, we'd get altair to handle this situation\n// better.\n// https://github.com/posit-dev/py-shinywidgets/issues/172\ndocument.addEventListener('shown.bs.tab', event => {\n    window.dispatchEvent(new Event('resize'));\n});\n// Our version of https://github.com/jupyter-widgets/widget-cookiecutter/blob/9694718/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L8\nfunction setBaseURL(x = '') {\n    const base_url = document.querySelector('body').getAttribute('data-base-url');\n    if (!base_url) {\n        document.querySelector('body').setAttribute('data-base-url', x);\n    }\n}\n// TypeGuard to safely check if an object has a method\nfunction hasMethod(obj, methodName) {\n    return typeof obj[methodName] === 'function';\n}\n\n\n//# sourceURL=webpack://@jupyter-widgets/shiny-embed-manager/./src/output.ts?");

/***/ }),

/***/ "./src/utils.ts":
/*!**********************!*\
  !*** ./src/utils.ts ***!
  \**********************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"Throttler\": () => (/* binding */ Throttler),\n/* harmony export */   \"jsonParse\": () => (/* binding */ jsonParse)\n/* harmony export */ });\n/* harmony import */ var base64_arraybuffer__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! base64-arraybuffer */ \"./node_modules/base64-arraybuffer/dist/base64-arraybuffer.es5.js\");\n\n// On the server, we're using jupyter_client.session.json_packer to serialize messages,\n// and it encodes binary data (i.e., buffers) as base64, so decode it before passing it\n// along to the comm logic\nfunction jsonParse(x) {\n    const msg = JSON.parse(x);\n    msg.buffers = msg.buffers.map((base64) => new DataView((0,base64_arraybuffer__WEBPACK_IMPORTED_MODULE_0__.decode)(base64)));\n    return msg;\n}\nclass Throttler {\n    constructor(wait = 100) {\n        if (wait < 0)\n            throw new Error(\"wait must be a positive number\");\n        this.wait = wait;\n        this._reset();\n    }\n    // Try to execute the function immediately, if it is not waiting\n    // If it is waiting, update the function to be called\n    throttle(fn) {\n        if (fn.length > 0)\n            throw new Error(\"fn must not take any arguments\");\n        if (this.isWaiting) {\n            // If the timeout is currently waiting, update the func to be called\n            this.fnToCall = fn;\n        }\n        else {\n            // If there is nothing waiting, call it immediately\n            // and start the throttling\n            fn();\n            this._setTimeout();\n        }\n    }\n    // Execute the function immediately and reset the timeout\n    // This is useful when the timeout is waiting and we want to\n    // execute the function immediately to not have events be out\n    // of order\n    flush() {\n        if (this.fnToCall)\n            this.fnToCall();\n        this._reset();\n    }\n    _setTimeout() {\n        this.timeoutId = setTimeout(() => {\n            if (this.fnToCall) {\n                this.fnToCall();\n                this.fnToCall = null;\n                // Restart the timeout as we just called the function\n                // This call is the key step of Throttler\n                this._setTimeout();\n            }\n            else {\n                this._reset();\n            }\n        }, this.wait);\n    }\n    _reset() {\n        this.fnToCall = null;\n        clearTimeout(this.timeoutId);\n        this.timeoutId = null;\n    }\n    get isWaiting() {\n        return this.timeoutId !== null;\n    }\n}\n\n\n\n//# sourceURL=webpack://@jupyter-widgets/shiny-embed-manager/./src/utils.ts?");

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