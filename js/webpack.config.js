const path = require('path');
const webpack = require('webpack');

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

const resolve = { extensions: ['.ts', '.js'] }
const plugins = [
  new webpack.DefinePlugin({
    // Needed for Blueprint. See https://github.com/palantir/blueprint/issues/4393
    'process.env': '{}',
  }),
]
const mode = "development"

module.exports = [
  {
    entry: './src/output.ts',
    output: {
      filename: 'output.js',
      path: path.resolve(__dirname, 'dist'),
      publicPath: 'dist/',
    },
    resolve,
    plugins,
    module: {rules: rules},
    mode,
    // TODO: why isn't this working?
    //externals: ["@jupyter-widgets/html-manager"]
  },
  {
    entry: './src/input.ts',
    output: {
      filename: 'input.js',
      path: path.resolve(__dirname, 'dist'),
      publicPath: 'dist/',
    },
    resolve,
    plugins,
    module: { rules: rules },
    mode,
    //externals: ["@jupyter-widgets/html-manager"]
  }
];
