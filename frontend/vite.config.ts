/// <reference types="vitest" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

/** Custom Vite Mock Plugin for API Server endpoints (REST & SSE Stream) */
function apiMockPlugin(): Plugin {
  const mockSessionStore: unknown[] = [];

  return {
    name: 'vite-plugin-api-mock',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!process.env.VITE_MOCK) {
          return next();
        }

        const url = req.url || '';

        // Mock POST /api/v1/auth/login
        if (url.includes('/api/v1/auth/login') && req.method === 'POST') {
          res.setHeader('Content-Type', 'application/json');
          res.setHeader('Set-Cookie', `sessionid=mock_session_${Date.now()}; Path=/;`);
          res.end(
            JSON.stringify({
              code: 0,
              message: 'User logged in successfully',
              data: {
                tenant_id: 1,
              },
            })
          );
          return;
        }

        // Mock POST /api/v1/chat/sessions
        if (url.includes('/api/v1/chat/sessions') && req.method === 'POST') {
          res.setHeader('Content-Type', 'application/json');
          let body = '';
          req.on('data', (chunk) => {
            body += chunk;
          });
          req.on('end', () => {
            let title = 'New Chat';
            try {
              const parsed = JSON.parse(body);
              if (parsed.title) title = parsed.title;
            } catch {
              // fallback
            }
            const chatSessionId = `cs_mock_${Date.now()}`;
            const newSession = {
              id: Date.now(),
              chat_session_id: chatSessionId,
              tenant_id: 1,
              user_id: 101,
              title,
              status: 1,
              create_ts: Math.floor(Date.now() / 1000),
              update_ts: Math.floor(Date.now() / 1000),
            };
            mockSessionStore.unshift(newSession);
            res.end(
              JSON.stringify({
                code: 0,
                message: 'Chat session created successfully',
                data: {
                  chat_session_id: chatSessionId,
                  session_info: newSession,
                },
              })
            );
          });
          return;
        }

        // Mock GET /api/v1/chat/sessions
        if (url.includes('/api/v1/chat/sessions') && req.method === 'GET') {
          res.setHeader('Content-Type', 'application/json');
          res.end(
            JSON.stringify({
              code: 0,
              message: 'Chat sessions retrieved successfully',
              data: {
                has_more: false,
                next_cursor: null,
                items: mockSessionStore,
              },
            })
          );
          return;
        }

        // Mock POST /api/v1/chat/message
        if (url.includes('/api/v1/chat/message') && req.method === 'POST') {
          res.setHeader('Content-Type', 'application/json');
          res.end(
            JSON.stringify({
              run_id: `run_mock_${Date.now()}`,
              thread_id: 'thread_mock_001',
              status: 'pending',
            })
          );
          return;
        }

        // Mock POST /api/v1/chat/resume
        if (url.includes('/api/v1/chat/resume') && req.method === 'POST') {
          res.setHeader('Content-Type', 'application/json');
          res.end(
            JSON.stringify({
              run_id: `run_mock_${Date.now()}`,
              thread_id: 'thread_mock_001',
              status: 'resumed',
            })
          );
          return;
        }

        // Mock POST /api/v1/chat/stream (SSE Stream)
        if (url.includes('/api/v1/chat/stream') && req.method === 'POST') {
          res.setHeader('Content-Type', 'text/event-stream');
          res.setHeader('Cache-Control', 'no-cache');
          res.setHeader('Connection', 'keep-alive');

          let body = '';
          req.on('data', (chunk) => {
            body += chunk;
          });

          req.on('end', () => {
            let userPrompt = 'Hello';
            try {
              const parsed = JSON.parse(body);
              if (parsed.message?.content) {
                userPrompt = parsed.message.content;
              }
            } catch {
              // fallback
            }

            res.write(`event: token\ndata: [Mock Response] I received your prompt: "${userPrompt}".\n\n`);
            
            setTimeout(() => {
              res.write(`event: token\ndata:  LangGraph Multi-Agent execution simulated successfully in mock mode.\n\n`);
            }, 300);

            setTimeout(() => {
              // Simulate Human-in-the-Loop Interrupt for demonstration
              if (userPrompt.toLowerCase().includes('refund') || userPrompt.toLowerCase().includes('interrupt')) {
                res.write(
                  `event: interrupt\ndata: ${JSON.stringify({
                    interrupt_id: `int_${Date.now()}`,
                    thread_id: 'thread_mock_001',
                    node_name: 'PolicyRefundCheck',
                    description: 'Approval required to process refund for order #99182.',
                    checkpoint_id: 'chk_1001',
                  })}\n\n`
                );
              }
              res.end();
            }, 600);
          });

          return;
        }

        next();
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), apiMockPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: process.env.VITE_MOCK
      ? {}
      : {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
            secure: false,
          },
        },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
  },
})
