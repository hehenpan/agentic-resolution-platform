/// <reference types="vitest" />
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

/** Custom Vite Mock Plugin for API Server endpoints (REST & SSE Stream) */
function apiMockPlugin(): Plugin {
  const mockSessionStore: unknown[] = [];
  const mockMessageStore: Record<string, unknown[]> = {};
  const mockReturnsStore: Record<number, any[]> = {};
  const mockFilesStore: any[] = [];

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
          let body = '';
          req.on('data', (chunk) => {
            body += chunk;
          });
          req.on('end', () => {
            let email = 'mock_user@example.com';
            try {
              const parsed = JSON.parse(body);
              if (parsed.email) email = parsed.email;
            } catch {
              // ignore
            }
            const isTenantAdmin = email.includes('admin');
            const userType = isTenantAdmin ? 'tenant_admin' : 'user';

            res.setHeader('Content-Type', 'application/json');
            res.setHeader('Set-Cookie', `sessionid=mock_session_${Date.now()}; Path=/;`);
            res.end(
              JSON.stringify({
                code: 0,
                message: 'User logged in successfully',
                data: {
                  user_id: isTenantAdmin ? 101 : 102,
                  email: email,
                  user_type: userType,
                  tenant_id: 1,
                },
              })
            );
          });
          return;
        }

        // Mock POST /api/v1/chat/sessions (Create session)
        if (url.replace(/\?.*$/, '') === '/api/v1/chat/sessions' && req.method === 'POST') {
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

        // Mock GET /api/v1/chat/sessions/:chat_session_id/messages
        if (/\/api\/v1\/chat\/sessions\/[^/]+\/messages/.test(url) && req.method === 'GET') {
          res.setHeader('Content-Type', 'application/json');
          if (url.includes('cursor=invalid')) {
            res.statusCode = 400;
            res.end(
              JSON.stringify({
                detail: 'Invalid cursor format: non-float timestamp string',
              })
            );
            return;
          }

          const match = url.match(/\/api\/v1\/chat\/sessions\/([^/]+)\/messages/);
          const chatSessionId = match ? match[1] : '';
          const items = mockMessageStore[chatSessionId] || [];

          res.end(
            JSON.stringify({
              code: 0,
              message: 'Chat history messages retrieved successfully',
              data: {
                has_more: false,
                next_cursor: null,
                items,
              },
            })
          );
          return;
        }

        // Mock POST /api/v1/chat/sessions/:chat_session_id/messages
        if (/\/api\/v1\/chat\/sessions\/[^/]+\/messages/.test(url) && req.method === 'POST') {
          let body = '';
          req.on('data', (chunk) => {
            body += chunk;
          });

          req.on('end', () => {
            let content = '';
            try {
              const parsed = JSON.parse(body);
              content = parsed.content || '';
            } catch {
              // Ignore body parse failure
            }

            // Form 1 Error Cases
            if (url.includes('/sessions/invalid_session/messages')) {
              res.statusCode = 500;
              res.setHeader('Content-Type', 'application/json');
              res.end(
                JSON.stringify({
                  detail: 'Chat session not found or access denied',
                })
              );
              return;
            }

            if (!content || content === 'error') {
              res.statusCode = 400;
              res.setHeader('Content-Type', 'application/json');
              res.end(
                JSON.stringify({
                  detail: 'content minimum length requirement not met',
                })
              );
              return;
            }

            const match = url.match(/\/api\/v1\/chat\/sessions\/([^/]+)\/messages/);
            const chatSessionId = match ? match[1] : 'cs_mock_default';
            if (!mockMessageStore[chatSessionId]) {
              mockMessageStore[chatSessionId] = [];
            }

            const now = Date.now();
            const userMsgItem = {
              id: mockMessageStore[chatSessionId].length + 1,
              event_id: `evt_mock_${now}_u`,
              chat_session_id: chatSessionId,
              thread_id: `thread_${chatSessionId}`,
              run_id: `run_${now}`,
              sender_type: 1, // USER
              event_kind: 'user_message',
              sequence: mockMessageStore[chatSessionId].length,
              payload_json: JSON.stringify({ content }),
              create_ts_ms: now,
            };
            mockMessageStore[chatSessionId].push(userMsgItem);

            res.statusCode = 200;
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');
            res.setHeader('X-Accel-Buffering', 'no');

            res.write(
              `event: user_message\ndata: ${JSON.stringify({
                event_id: userMsgItem.event_id,
                kind: 'user_message',
                content,
              })}\n\n`
            );

            // Interrupt Triggers Map for extensible mock negotiation
            const interruptTriggers: Record<
              string,
              { schema_id: string; prompt: string; input_schema: Record<string, unknown> }
            > = {
              getuserbyemail: {
                schema_id: 'human_input.get_user.v1',
                prompt: 'Please enter customer email to look up user information.',
                input_schema: {
                  type: 'object',
                  properties: {
                    email: { type: 'string', description: 'Customer email address' },
                    llm_text: { type: 'string', description: 'Raw natural language text' },
                  },
                },
              },
              getordersbyemail: {
                schema_id: 'human_input.get_orders.v1',
                prompt: 'Please enter customer email to query order history.',
                input_schema: {
                  type: 'object',
                  properties: {
                    email: { type: 'string', description: 'Customer email address' },
                    llm_text: { type: 'string', description: 'Raw natural language text' },
                  },
                },
              },
              getorderdetails: {
                schema_id: 'human_input.get_order_details.v1',
                prompt: 'Please enter positive Order ID to look up order details.',
                input_schema: {
                  type: 'object',
                  properties: {
                    order_id: { type: 'integer', description: 'Positive order identifier' },
                    llm_text: { type: 'string', description: 'Raw natural language text' },
                  },
                },
              },
              getreturnbyorder: {
                schema_id: 'human_input.get_returns_by_order.v1',
                prompt: 'Please enter positive Order ID to look up associated return request history.',
                input_schema: {
                  type: 'object',
                  properties: {
                    order_id: { type: 'integer', description: 'Positive order identifier' },
                    llm_text: { type: 'string', description: 'Raw natural language text' },
                  },
                },
              },
              createreturn: {
                schema_id: 'human_input.create_return_request.v1',
                prompt: 'Please enter return details (Order ID, Customer ID, Reason Code, Item Condition) to submit return request.',
                input_schema: {
                  $defs: {
                    AgentReturnReason: {
                      enum: ['change_of_mind', 'damaged', 'wrong_item', 'not_as_described', 'late_delivery'],
                      type: 'string',
                    },
                    AgentItemCondition: {
                      enum: ['unopened', 'opened', 'used', 'damaged'],
                      type: 'string',
                    },
                  },
                  type: 'object',
                  properties: {
                    order_id: { type: 'integer', description: 'Positive order identifier' },
                    customer_id: { type: 'integer', description: 'Positive customer identifier' },
                    reason_code: { $ref: '#/$defs/AgentReturnReason' },
                    item_condition: { $ref: '#/$defs/AgentItemCondition' },
                    reason_text: { type: 'string', description: 'Additional explanation text' },
                  },
                },
              },
              getreturnbycustomer: {
                schema_id: 'human_input.get_returns_by_customer.v1',
                prompt: 'Please enter positive Customer ID to look up customer return history.',
                input_schema: {
                  type: 'object',
                  properties: {
                    customer_id: { type: 'integer', description: 'Positive customer identifier' },
                    llm_text: { type: 'string', description: 'Raw natural language text' },
                  },
                },
              },
            };

            const normalizedContent = content.trim().toLowerCase();
            const matchedTrigger = interruptTriggers[normalizedContent];

            if (matchedTrigger) {
              const interruptId = `intr_mock_${normalizedContent}_${now}`;
              setTimeout(() => {
                res.write(
                  `event: agent.human_input_requested\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_hir`,
                    kind: 'agent.human_input_requested',
                    thread_id: `thread_${chatSessionId}`,
                    run_id: `run_${now}`,
                    sequence: 1,
                    interrupt_id: interruptId,
                    request: {
                      prompt: matchedTrigger.prompt,
                      schema_id: matchedTrigger.schema_id,
                      input_schema: matchedTrigger.input_schema,
                      allowed_actions: ['submit', 'cancel'],
                    },
                    resume_cursor: {
                      checkpoint_id: `chk_mock_${now}`,
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_interrupted\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_ri`,
                    kind: 'agent.run_interrupted',
                    thread_id: `thread_${chatSessionId}`,
                    run_id: `run_${now}`,
                    sequence: 2,
                    interrupt_ids: [interruptId],
                    schema_id: matchedTrigger.schema_id,
                    request: {
                      prompt: matchedTrigger.prompt,
                      schema_id: matchedTrigger.schema_id,
                      input_schema: matchedTrigger.input_schema,
                      allowed_actions: ['submit', 'cancel'],
                    },
                  })}\n\n`
                );
                res.end();
              }, 200);
              return;
            }

            if (normalizedContent === 'dedupe-order-test') {
              const duplicateEventId = `evt_mock_${now}_dedupe`;
              const firstOutputText = '[Mock SSE Stream] First deduped response.';
              const duplicateOutputText = '[Mock SSE Stream] Duplicate response should be ignored.';
              const createdAt = Math.floor((now + 300) / 1000);
              const agentMsgItem = {
                id: mockMessageStore[chatSessionId].length + 1,
                event_id: duplicateEventId,
                chat_session_id: chatSessionId,
                thread_id: `thread_${chatSessionId}`,
                run_id: `run_${now}`,
                sender_type: 2,
                event_kind: 'agent.output_produced',
                sequence: mockMessageStore[chatSessionId].length,
                payload_json: JSON.stringify({ output: { parts: [{ kind: 'text', text: firstOutputText }] } }),
                create_ts_ms: now + 300,
              };

              setTimeout(() => {
                mockMessageStore[chatSessionId].push(agentMsgItem);
                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: duplicateEventId,
                    kind: 'agent.output_produced',
                    thread_id: `thread_${chatSessionId}`,
                    run_id: `run_${now}`,
                    sequence: 1,
                    created_at: createdAt,
                    output: {
                      output_id: `out_mock_${now}_dedupe`,
                      parts: [{ kind: 'text', text: firstOutputText }],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: duplicateEventId,
                    kind: 'agent.output_produced',
                    thread_id: `thread_${chatSessionId}`,
                    run_id: `run_${now}`,
                    sequence: 2,
                    created_at: createdAt + 1,
                    output: {
                      output_id: `out_mock_${now}_dedupe`,
                      parts: [{ kind: 'text', text: duplicateOutputText }],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_completed\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_c`,
                    kind: 'agent.run_completed',
                    thread_id: `thread_${chatSessionId}`,
                    run_id: `run_${now}`,
                    sequence: 3,
                    created_at: createdAt + 2,
                  })}\n\n`
                );
                res.end();
              }, 300);
              return;
            }

            const agentOutputText = `[Mock SSE Stream] Received message: "${content}"`;
            const agentMsgItem = {
              id: mockMessageStore[chatSessionId].length + 1,
              event_id: `evt_mock_${now}_a`,
              chat_session_id: chatSessionId,
              thread_id: `thread_${chatSessionId}`,
              run_id: `run_${now}`,
              sender_type: 2, // AGENT
              event_kind: 'agent.output_produced',
              sequence: mockMessageStore[chatSessionId].length,
              payload_json: JSON.stringify({ output: { parts: [{ text: agentOutputText }] } }),
              create_ts_ms: now + 300,
            };

            setTimeout(() => {
              mockMessageStore[chatSessionId].push(agentMsgItem);
              res.write(
                `event: agent.output_produced\ndata: ${JSON.stringify({
                  event_id: agentMsgItem.event_id,
                  kind: 'agent.output_produced',
                  thread_id: `thread_${chatSessionId}`,
                  run_id: `run_${now}`,
                  sequence: 1,
                  created_at: Math.floor((now + 300) / 1000),
                  output: {
                    output_id: `out_mock_${now}`,
                    parts: [{ kind: 'text', text: agentOutputText }],
                  },
                })}\n\n`
              );

              res.write(
                `event: agent.run_completed\ndata: ${JSON.stringify({
                  event_id: `evt_mock_${now}_c`,
                  kind: 'agent.run_completed',
                  thread_id: `thread_${chatSessionId}`,
                  run_id: `run_${now}`,
                  sequence: 2,
                  created_at: Math.floor((now + 400) / 1000),
                })}\n\n`
              );
              res.end();
            }, 300);
          });
          return;
        }

        // Mock POST /api/v1/chat/sessions/:chat_session_id/resume
        if (/\/api\/v1\/chat\/sessions\/[^/]+\/resume/.test(url) && req.method === 'POST') {
          let body = '';
          req.on('data', (chunk) => {
            body += chunk;
          });

          req.on('end', () => {
            let resumeReq: {
              schema_id?: string;
              resume_payload?: Record<string, unknown>;
              chat_session_id?: string;
              thread_id?: string;
              interrupt_id?: string;
            } = {};

            try {
              resumeReq = JSON.parse(body);
            } catch {
              // fallback
            }

            const now = Date.now();
            const schemaId = resumeReq.schema_id || 'human_input.get_user.v1';
            const resumePayload = resumeReq.resume_payload || {};

            // Extract email from email property or llm_text
            let emailVal = String(resumePayload.email || '');
            if (!emailVal && resumePayload.llm_text) {
              const text = String(resumePayload.llm_text);
              const emailMatch = text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
              emailVal = emailMatch ? emailMatch[0] : text;
            }
            if (!emailVal) {
              emailVal = 'customer@example.com';
            }

            res.statusCode = 200;
            res.setHeader('Content-Type', 'text/event-stream');
            res.setHeader('Cache-Control', 'no-cache');
            res.setHeader('Connection', 'keep-alive');
            res.setHeader('X-Accel-Buffering', 'no');

            if (schemaId === 'human_input.get_orders.v1') {
              const textMessage = `Successfully queried orders for customer (${emailVal}).`;
              const ordersData = {
                customer_email: emailVal,
                orders: [
                  {
                    order_id: 88412,
                    user_id: 1001,
                    email: emailVal,
                    status: 1, // PAID
                    total_amount: 199.99,
                    created_ts: 1700000000,
                  },
                  {
                    order_id: 88413,
                    user_id: 1001,
                    email: emailVal,
                    status: 3, // COMPLETED
                    total_amount: 89.5,
                    created_ts: 1699500000,
                  },
                ],
              };

              setTimeout(() => {
                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_out`,
                    kind: 'agent.output_produced',
                    output: {
                      output_id: `out_mock_${now}`,
                      parts: [
                        { kind: 'text', text: textMessage },
                        {
                          kind: 'structured_data',
                          schema_id: 'ecommerce.orders_result.v1',
                          data: ordersData,
                        },
                      ],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_completed\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_rc`,
                    kind: 'agent.run_completed',
                  })}\n\n`
                );
                res.end();
              }, 300);
            } else if (schemaId === 'human_input.get_order_details.v1') {
              let orderIdVal = Number(resumePayload.order_id || 0);
              if (!orderIdVal && resumePayload.llm_text) {
                const text = String(resumePayload.llm_text);
                const match = text.match(/\d+/);
                orderIdVal = match ? parseInt(match[0], 10) : 88412;
              }
              if (!orderIdVal) orderIdVal = 88412;

              const textMessage = `Successfully retrieved order details for Order #${orderIdVal}.`;
              const orderDetailsData = {
                exists: true,
                order: {
                  order_id: orderIdVal,
                  user_id: 1001,
                  email: 'alex@example.com',
                  status: 1, // PAID
                  total_amount: 199.99,
                  created_ts: 1753236000,
                },
                items: [
                  {
                    item_id: 1,
                    sku_id: 501,
                    sku_code: 'SKU-PRO-01',
                    name: 'Wireless Noise-Canceling Headphones',
                    quantity: 1,
                    price: 149.99,
                  },
                  {
                    item_id: 2,
                    sku_id: 502,
                    sku_code: 'SKU-ACC-02',
                    name: 'Hard Shell Carrying Case',
                    quantity: 1,
                    price: 50.0,
                  },
                ],
              };

              setTimeout(() => {
                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_out`,
                    kind: 'agent.output_produced',
                    output: {
                      output_id: `out_mock_${now}`,
                      parts: [
                        { kind: 'text', text: textMessage },
                        {
                          kind: 'structured_data',
                          schema_id: 'ecommerce.order_details_result.v1',
                          data: orderDetailsData,
                        },
                      ],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_completed\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_rc`,
                    kind: 'agent.run_completed',
                  })}\n\n`
                );
                res.end();
              }, 300);
            } else if (schemaId === 'human_input.get_returns_by_order.v1') {
              let orderIdVal = Number(resumePayload.order_id || 0);
              if (!orderIdVal && resumePayload.llm_text) {
                const match = String(resumePayload.llm_text).match(/\d+/);
                orderIdVal = match ? parseInt(match[0], 10) : 88412;
              }
              if (!orderIdVal) orderIdVal = 88412;

              const textMessage = `Successfully retrieved return details for Order #${orderIdVal}.`;
              const returnsData = {
                order_id: orderIdVal,
                return_request: {
                  return_request_id: 9001,
                  order_id: orderIdVal,
                  customer_id: 1001,
                  status: 1, // APPROVED
                  reason_code: 1, // DAMAGED
                  reason_text: 'Product arrived with damaged outer packaging.',
                  item_condition: 3, // DAMAGED
                  requested_at: 1753236000,
                  created_at: 1753236000,
                  updated_at: 1753236000,
                },
              };

              setTimeout(() => {
                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_out`,
                    kind: 'agent.output_produced',
                    output: {
                      output_id: `out_mock_${now}`,
                      parts: [
                        { kind: 'text', text: textMessage },
                        {
                          kind: 'structured_data',
                          schema_id: 'ecommerce.returns_by_order_result.v1',
                          data: returnsData,
                        },
                      ],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_completed\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_rc`,
                    kind: 'agent.run_completed',
                  })}\n\n`
                );
                res.end();
              }, 300);
            } else if (schemaId === 'human_input.create_return_request.v1') {
              let orderIdVal = Number(resumePayload.order_id || 0);
              let customerIdVal = Number(resumePayload.customer_id || 0);
              const reasonCodeVal = String(resumePayload.reason_code || 'damaged');
              const itemConditionVal = String(resumePayload.item_condition || 'opened');
              const reasonTextVal = String(resumePayload.reason_text || 'Item damaged during transit.');

              if (!orderIdVal) orderIdVal = 88412;
              if (!customerIdVal) customerIdVal = 1001;

              const reasonCodeMap: Record<string, number> = {
                change_of_mind: 0,
                damaged: 1,
                wrong_item: 2,
                not_as_described: 3,
                late_delivery: 4,
              };

              const conditionMap: Record<string, number> = {
                unopened: 0,
                opened: 1,
                used: 2,
                damaged: 3,
              };

              const textMessage = `Successfully created return request for Order #${orderIdVal}.`;
              const returnReqObj = {
                return_request_id: 9901,
                order_id: orderIdVal,
                customer_id: customerIdVal,
                status: 0, // REQUESTED
                reason_code: reasonCodeMap[reasonCodeVal] ?? 1,
                reason_text: reasonTextVal,
                item_condition: conditionMap[itemConditionVal] ?? 1,
                requested_at: 1753236000,
                created_at: 1753236000,
                updated_at: 1753236000,
              };

              if (!mockReturnsStore[customerIdVal]) {
                mockReturnsStore[customerIdVal] = [];
              }
              mockReturnsStore[customerIdVal].push(returnReqObj);

              const createReturnData = {
                success: true,
                return_request: returnReqObj,
                error_message: null,
              };

              setTimeout(() => {
                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_out`,
                    kind: 'agent.output_produced',
                    output: {
                      output_id: `out_mock_${now}`,
                      parts: [
                        { kind: 'text', text: textMessage },
                        {
                          kind: 'structured_data',
                          schema_id: 'ecommerce.create_return_result.v1',
                          data: createReturnData,
                        },
                      ],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_completed\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_rc`,
                    kind: 'agent.run_completed',
                  })}\n\n`
                );
                res.end();
              }, 300);
            } else if (schemaId === 'human_input.get_returns_by_customer.v1') {
              let customerIdVal = Number(resumePayload.customer_id || 0);
              if (!customerIdVal && resumePayload.llm_text) {
                const match = String(resumePayload.llm_text).match(/\d+/);
                customerIdVal = match ? parseInt(match[0], 10) : 1001;
              }
              if (!customerIdVal) customerIdVal = 1001;

              const customerReturns = mockReturnsStore[customerIdVal] || [];
              const textMessage =
                customerReturns.length > 0
                  ? `Successfully retrieved ${customerReturns.length} return request(s) for Customer #${customerIdVal}.`
                  : `No return request history found for Customer #${customerIdVal}.`;

              const returnsData = {
                customer_id: customerIdVal,
                returns: customerReturns,
              };

              setTimeout(() => {
                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_out`,
                    kind: 'agent.output_produced',
                    output: {
                      output_id: `out_mock_${now}`,
                      parts: [
                        { kind: 'text', text: textMessage },
                        {
                          kind: 'structured_data',
                          schema_id: 'ecommerce.returns_by_customer_result.v1',
                          data: returnsData,
                        },
                      ],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_completed\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_rc`,
                    kind: 'agent.run_completed',
                  })}\n\n`
                );
                res.end();
              }, 300);
            } else {
              // Default to get_user response
              const textMessage = `Successfully retrieved user information for customer (${emailVal}).`;
              const userData = {
                exists: true,
                user_id: 1001,
                email: emailVal,
                user_name: 'Alex Customer',
              };

              setTimeout(() => {
                res.write(
                  `event: agent.output_produced\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_out`,
                    kind: 'agent.output_produced',
                    output: {
                      output_id: `out_mock_${now}`,
                      parts: [
                        { kind: 'text', text: textMessage },
                        {
                          kind: 'structured_data',
                          schema_id: 'ecommerce.user_result.v1',
                          data: userData,
                        },
                      ],
                    },
                  })}\n\n`
                );

                res.write(
                  `event: agent.run_completed\ndata: ${JSON.stringify({
                    event_id: `evt_mock_${now}_rc`,
                    kind: 'agent.run_completed',
                  })}\n\n`
                );
                res.end();
              }, 300);
            }
          });
          return;
        }

        // Mock GET /api/v1/chat/sessions
        if (url.replace(/\?.*$/, '') === '/api/v1/chat/sessions' && req.method === 'GET') {
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

        // Mock GET /api/v1/files (file list)
        if (url.replace(/\?.*$/, '') === '/api/v1/files' && req.method === 'GET') {
          res.setHeader('Content-Type', 'application/json');
          // Sort by create_ts descending (newest first)
          const sorted = [...mockFilesStore].sort((a, b) => b.create_ts - a.create_ts);
          res.end(
            JSON.stringify({
              code: 0,
              message: 'Success',
              data: {
                items: sorted,
                last_cursor: '',
              },
            })
          );
          return;
        }

        // Mock POST /api/v1/files/upload (file upload)
        if (url.replace(/\?.*$/, '') === '/api/v1/files/upload' && req.method === 'POST') {
          const chunks: Buffer[] = [];
          req.on('data', (chunk: Buffer) => {
            chunks.push(chunk);
          });
          req.on('end', () => {
            const body = Buffer.concat(chunks).toString();
            // Extract filename from multipart Content-Disposition header
            let fileName = 'unnamed_file';
            const filenameMatch = body.match(/filename="([^"]+)"/);
            if (filenameMatch) {
              fileName = filenameMatch[1];
            }
            // Extract file extension as type
            const extMatch = fileName.match(/\.([^.]+)$/);
            const fileType = extMatch ? extMatch[1].toLowerCase() : 'unknown';
            const contentLength = Number(req.headers['content-length'] || 0);

            const now = Date.now();
            const fileId = Math.floor(Math.random() * 900000) + 100000;
            const newFile = {
              file_id: fileId,
              file_name: fileName,
              file_size: contentLength,
              file_type: fileType,
              file_md5_hash: `mock_md5_${now}`,
              owner_user_id: 101,
              owner_email: 'admin@tenant.com',
              create_ts: Math.floor(now / 1000),
              status: 1,
              vector_db_sync_status: 0,
            };
            mockFilesStore.push(newFile);

            res.statusCode = 201;
            res.setHeader('Content-Type', 'application/json');
            res.end(
              JSON.stringify({
                code: 0,
                message: 'File uploaded successfully',
                data: {
                  file_id: fileId,
                  file_name: fileName,
                  file_size: contentLength,
                },
              })
            );
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
