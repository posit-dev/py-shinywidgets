/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./src/runtime-register.ts":
/*!*********************************!*\
  !*** ./src/runtime-register.ts ***!
  \*********************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/******************************************************************************\n * AMD registration for the shinywidgets runtime.\n *\n * This is a plain script (not an AMD module): it runs after libembed-amd.js\n * has assigned `window.shinywidgetsRuntime` and before output.js starts\n * requiring widget modules. It defines the official module IDs as static\n * named aliases of the one coherent runtime, so third-party widget modules\n * and our own output bundle share the exact same base/controls/html\n * constructors (no duplicate Backbone/base/Lumino bundle).\n ******************************************************************************/\nconst runtime = window\n    .shinywidgetsRuntime;\ndefine(\"shinywidgets-runtime\", [], () => runtime);\ndefine(\"@jupyter-widgets/base\", [\"shinywidgets-runtime\"], (r) => r.base);\ndefine(\"@jupyter-widgets/controls\", [\"shinywidgets-runtime\"], (r) => r.controls);\ndefine(\"@jupyter-widgets/html-manager\", [\"shinywidgets-runtime\"], (r) => r.html);\ndefine(\"shinywidgets-internals\", [\"shinywidgets-runtime\"], (r) => r.internals);\n\n\n\n//# sourceURL=webpack://@jupyter-widgets/shiny-embed-manager/./src/runtime-register.ts?");

/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The require scope
/******/ 	var __webpack_require__ = {};
/******/ 	
/************************************************************************/
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
/******/ 	var __webpack_exports__ = {};
/******/ 	__webpack_modules__["./src/runtime-register.ts"](0, __webpack_exports__, __webpack_require__);
/******/ 	
/******/ })()
;