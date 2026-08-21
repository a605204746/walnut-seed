import { defineConfig } from '@vben/vite-config';

export default defineConfig(async () => {
  return {
    application: {},
    vite: {
      server: {
        proxy: {
          '/api': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ''),
            // 后端服务地址
            target: 'http://localhost:8011',
            ws: true,
          },
          // 上传文件访问：后端返回中性路径 /upload/{key}，本机开发经此代理到后端
          '/upload': {
            changeOrigin: true,
            target: 'http://localhost:8011',
          },
        },
      },
    },
  };
}) as any;
