/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: [],
  experimental: {},
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "@fbgroup/api-client": require("path").resolve(
        __dirname,
        "../../packages/api-client/src/index.ts"
      ),
    };
    return config;
  },
};

module.exports = nextConfig;
