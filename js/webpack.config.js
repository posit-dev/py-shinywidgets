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
        copy: [{ source: outputPath + '/*', destination: '../ipyshiny/static' }]
      }
    }
  })
]
const mode = "development"

module.exports = [
  {
    entry: './src/output.ts',
    output: {
      filename: 'output.js',
      path: outputPath,
      // I think this is needed for externals to work
      //libraryTarget: 'amd',
      publicPath: 'dist/',
    },
    resolve,
    plugins,
    module: {rules: rules},
    mode,
    // TODO: this bundle is quite large because html-manager is large. Find a way to
    // make it smaller (which seems possible given we're already sourcing libembed?)
    //externals: {"@jupyter-widgets/html-manager": "@jupyter-widgets/html-manager"}
  }
];
