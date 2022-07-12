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
    entry: './src/output.ts',
    output: {
      filename: 'output.js',
      path: outputPath,
      // amd is needed for externals to work and require is for immediately invoking
      // https://webpack.js.org/configuration/output/#librarytarget-amd-require
      libraryTarget: "amd-require",
      publicPath: 'dist/',
    },
    resolve,
    plugins,
    module: {rules: rules},
    // Since we're bundling hardly any dependencies, just use development (at least for now)
    mode: "development",
    // These dependencies are brought in externally via ipywidget's "libembed" bundle
    // which is configured to load 3rd party widgets dynamically via RequireJS
    // https://github.com/jupyter-widgets/ipywidgets/blob/88cec8/packages/html-manager/webpack.config.js#L98
    externals: [
      "@jupyter-widgets/base",
      "@jupyter-widgets/controls",
      "@jupyter-widgets/html-manager",
    ]
  },
 ];
