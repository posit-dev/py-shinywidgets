const path = require('path');
const webpack = require('webpack');
const FileManagerPlugin = require('filemanager-webpack-plugin');

const rules = [
  { test: /\.tsx?$/, use: 'ts-loader', exclude: /node_modules/ },
  { test: /\.css$/, use: ['style-loader', 'css-loader'] },
  // jquery-ui loads some images
  { test: /\.(jpg|png|gif)$/, use: 'file-loader' },
  // required to load font-awesome
  {
    test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
    use: {
      loader: 'url-loader',
      options: {
        limit: 10000,
        mimetype: 'application/font-woff',
      },
    },
  },
  {
    test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
    use: {
      loader: 'url-loader',
      options: {
        limit: 10000,
        mimetype: 'application/font-woff',
      },
    },
  },
  {
    test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
    use: {
      loader: 'url-loader',
      options: {
        limit: 10000,
        mimetype: 'application/octet-stream',
      },
    },
  },
  { test: /\.eot(\?v=\d+\.\d+\.\d+)?$/, use: 'file-loader' },
  {
    test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
    use: {
      loader: 'url-loader',
      options: {
        limit: 10000,
        mimetype: 'image/svg+xml',
      },
    },
  },
]

const resolve = { extensions: ['.ts', '.js'] };
const outputPath = path.resolve(__dirname, 'dist');
const plugins = [
  new webpack.DefinePlugin({
    // Needed for Blueprint. See https://github.com/palantir/blueprint/issues/4393
    'process.env': '{}',
  }),
  // Copy the output files to the python package
  new FileManagerPlugin({
    events: {
      onEnd: {
        copy: [{ source: outputPath + '/*', destination: '../shinywidgets/static' }]
      }
    }
  })
]


module.exports = [
  {
    // The widget runtime: one coherent compilation of the official
    // @jupyter-widgets packages and the internals our lifecycle code uses.
    // Built from source (replaces the downloaded html-manager libembed-amd.js
    // bundle) and exposed as window.shinywidgetsRuntime; runtime-register.js
    // aliases the official AMD module IDs onto it. It executes as a plain
    // script so webpack derives publicPath (font/chunk URLs) from this
    // script's own URL ("auto").
    entry: './src/runtime.ts',
    output: {
      filename: 'libembed-amd.js',
      path: outputPath,
      library: { name: 'shinywidgetsRuntime', type: 'var' },
      publicPath: 'auto',
    },
    resolve,
    plugins: [
      ...plugins,
      // The ipywidgets-7 compatibility packages (controls7) import
      // '@jupyter-widgets/base' but must be wired to the ipywidgets-7 base
      // (base7), not the hoisted ipywidgets-8 base v6 -- matching the
      // official libembed-amd.js bundle.
      new webpack.NormalModuleReplacementPlugin(
        /^@jupyter-widgets\/base$/,
        (resource) => {
          if (resource.context.includes('controls7')) {
            resource.request = '@jupyter-widgets/base7';
          }
        }
      ),
    ],
    module: {rules: rules},
    mode: "development",
  },
  {
    // Static named AMD aliases mapping the official module IDs onto the
    // runtime namespaces. Must load after libembed-amd.js and before
    // output.js.
    entry: './src/runtime-register.ts',
    output: {
      filename: 'runtime-register.js',
      path: outputPath,
      publicPath: 'auto',
    },
    resolve,
    plugins,
    module: {rules: rules},
    mode: "development",
  },
  {
    entry: './src/output.ts',
    output: {
      filename: 'output.js',
      path: outputPath,
      // amd is needed for externals to work and require is for immediately invoking
      // https://webpack.js.org/configuration/output/#librarytarget-amd-require
      libraryTarget: "amd-require",
      publicPath: 'auto',
    },
    resolve,
    plugins,
    module: {rules: rules},
    // Since we're bundling hardly any dependencies, just use development (at least for now)
    mode: "development",
    // These dependencies are brought in externally from the runtime build
    // (libembed-amd.js) via the AMD aliases registered by runtime-register.js
    externals: [
      "@jupyter-widgets/base",
      "@jupyter-widgets/controls",
      "@jupyter-widgets/html-manager",
      "shinywidgets-internals",
    ]
  },
 ];
