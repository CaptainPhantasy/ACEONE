/**
 * SIP Inbound Call Webhook
 * Handles incoming phone calls and routes them to LiveKit rooms with agent dispatch
 */

import { NextRequest, NextResponse } from "next/server";
import { createHmac, timingSafeEqual } from "node:crypto";
import {
  AccessToken,
  RoomServiceClient,
  AgentDispatchClient,
} from "livekit-server-sdk";
import { z } from "zod";

// Environment variables validation
const envSchema = z.object({
  LK_URL: z.string().url(),
  LK_API_KEY: z.string().min(1),
  LK_API_SECRET: z.string().min(1),
  AGENT_NAME: z.string().default("claudevoice-agent"),
  WEBHOOK_SECRET: z.string().min(32),
});

class ConfigurationError extends Error {}

function getServices() {
  const parsed = envSchema.safeParse(process.env);
  if (!parsed.success) {
    throw new ConfigurationError("Webhook environment is incomplete or invalid");
  }

  const env = parsed.data;
  return {
    env,
    roomService: new RoomServiceClient(
      env.LK_URL,
      env.LK_API_KEY,
      env.LK_API_SECRET,
    ),
    agentClient: new AgentDispatchClient(
      env.LK_URL,
      env.LK_API_KEY,
      env.LK_API_SECRET,
    ),
  };
}

// Request body schema
const sipRequestSchema = z.object({
  from: z.string(),
  to: z.string(),
  callId: z.string().optional(),
  trunkId: z.string().optional(),
  metadata: z.record(z.string(), z.string()).optional(),
});

// Response types
interface SIPResponse {
  join_room?: {
    room: string;
    token: string;
    participant_identity?: string;
    participant_name?: string;
    participant_metadata?: string;
  };
  reject?: {
    reason?: string;
    status_code?: number;
  };
}

/**
 * Verify webhook signature for security
 */
function verifyWebhookSignature(
  body: string,
  signature: string | null,
  secret: string
): boolean {
  if (!signature) return false;

  const expectedSignature = createHmac('sha256', secret)
    .update(body)
    .digest('hex');
  const supplied = Buffer.from(signature);
  const expected = Buffer.from(`sha256=${expectedSignature}`);
  return supplied.length === expected.length && timingSafeEqual(supplied, expected);
}

/**
 * Format phone number for display
 */
function formatPhoneNumber(number: string): string {
  // Remove any non-digit characters
  const digits = number.replace(/\D/g, '');

  // Format based on length
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  } else if (digits.length === 11 && digits[0] === '1') {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }

  return number; // Return original if format unknown
}

/**
 * Check if phone number is blocked
 */
async function isBlockedNumber(phoneNumber: string): Promise<boolean> {
  // Implement blocklist checking
  // This could query a database or use a service
  const blocklist = process.env.BLOCKED_NUMBERS?.split(',') || [];
  return blocklist.some(blocked => phoneNumber.includes(blocked));
}

/**
 * Log call for analytics
 */
async function logCall(
  from: string,
  to: string,
  roomName: string,
  status: string
): Promise<void> {
  console.log(JSON.stringify({
    type: 'call_log',
    timestamp: new Date().toISOString(),
    from,
    to,
    room: roomName,
    status,
  }));

  // In production, send to analytics service
  // await analyticsClient.track({...})
}

/**
 * Main POST handler for inbound SIP calls
 */
export async function POST(req: NextRequest) {
  try {
    const { env, roomService, agentClient } = getServices();
    const rawBody = await req.text();

    const signature = req.headers.get('x-webhook-signature');
    if (!verifyWebhookSignature(rawBody, signature, env.WEBHOOK_SECRET)) {
      console.error('Invalid webhook signature');
      return NextResponse.json(
        { reject: { reason: 'Unauthorized', status_code: 401 } } as SIPResponse,
        { status: 401 }
      );
    }

    // Parse and validate request body
    const body = JSON.parse(rawBody);
    const validatedData = sipRequestSchema.parse(body);
    const { from, to, callId, trunkId, metadata } = validatedData;

    console.log(`Incoming call: ${from} -> ${to} (Call ID: ${callId})`);

    // Check blocklist
    if (await isBlockedNumber(from)) {
      console.log(`Blocked number: ${from}`);
      await logCall(from, to, '', 'blocked');
      return NextResponse.json({
        reject: {
          reason: 'Number not in service',
          status_code: 503
        }
      } as SIPResponse);
    }

    // Generate unique room name
    const timestamp = Date.now();
    const randomId = Math.random().toString(36).substring(2, 9);
    const roomName = `call-${timestamp}-${randomId}`;

    // Prepare room metadata
    const roomMetadata = {
      type: 'phone_call',
      from_number: from,
      to_number: to,
      call_id: callId,
      trunk_id: trunkId,
      started_at: new Date().toISOString(),
      ...metadata
    };

    // Create room options
    const roomOptions = {
      name: roomName,
      metadata: JSON.stringify(roomMetadata),
      emptyTimeout: 300, // 5 minutes
      maxParticipants: 2, // Caller + Agent
    };

    console.log(`Creating room: ${roomName}`);

    // Create the room
    try {
      await roomService.createRoom(roomOptions);
    } catch (error) {
      console.error('Failed to create room:', error);
      await logCall(from, to, roomName, 'room_creation_failed');
      return NextResponse.json({
        reject: {
          reason: 'Service temporarily unavailable',
          status_code: 503
        }
      } as SIPResponse);
    }

    // Dispatch agent to the room
    const agentMetadata = {
      type: 'inbound_call',
      from: from,
      to: to,
      formatted_from: formatPhoneNumber(from),
      call_id: callId,
      is_telephony: true
    };

    console.log(`Dispatching agent: ${env.AGENT_NAME}`);

    try {
      await agentClient.createDispatch(roomName, env.AGENT_NAME, {
        metadata: JSON.stringify(agentMetadata),
      });
    } catch (error) {
      console.error('Failed to dispatch agent:', error);
      // Clean up room if agent dispatch fails
      await roomService.deleteRoom(roomName);
      await logCall(from, to, roomName, 'agent_dispatch_failed');
      return NextResponse.json({
        reject: {
          reason: 'No agents available',
          status_code: 503
        }
      } as SIPResponse);
    }

    // Generate participant token
    const participantIdentity = `caller-${from.replace(/\D/g, '')}`;
    const participantName = `Caller ${formatPhoneNumber(from)}`;

    const token = new AccessToken(
      env.LK_API_KEY,
      env.LK_API_SECRET,
      {
        identity: participantIdentity,
        ttl: 3600, // 1 hour
        metadata: JSON.stringify({
          phone_number: from,
          is_caller: true
        }),
        name: participantName
      }
    );

    // Grant room permissions
    token.addGrant({
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true,
    });

    const jwt = await token.toJwt();

    console.log(`Call setup complete: ${roomName}`);
    await logCall(from, to, roomName, 'connected');

    // Return success response
    const response: SIPResponse = {
      join_room: {
        room: roomName,
        token: jwt,
        participant_identity: participantIdentity,
        participant_name: participantName,
        participant_metadata: JSON.stringify({
          phone_number: from,
          formatted_number: formatPhoneNumber(from),
          call_type: 'inbound'
        })
      }
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Webhook error:', error);

    if (error instanceof ConfigurationError) {
      return NextResponse.json({
        reject: {
          reason: 'Service is not configured',
          status_code: 503
        }
      } as SIPResponse, { status: 503 });
    }

    // Log error details
    if (error instanceof z.ZodError) {
      console.error('Validation error:', error.issues);
      return NextResponse.json({
        reject: {
          reason: 'Invalid request',
          status_code: 400
        }
      } as SIPResponse, { status: 400 });
    }

    // Generic error response
    return NextResponse.json({
      reject: {
        reason: 'Internal server error',
        status_code: 500
      }
    } as SIPResponse, { status: 500 });
  }
}

/**
 * GET handler for health check
 */
export async function GET() {
  try {
    const { env, roomService } = getServices();
    // Test LiveKit connection
    const rooms = await roomService.listRooms();

    return NextResponse.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      livekit: {
        connected: true,
        url: env.LK_URL,
        agent: env.AGENT_NAME
      },
      rooms_count: rooms.length
    });
  } catch (error) {
    console.error('Health check failed:', error);
    return NextResponse.json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: 'Failed to connect to LiveKit'
    }, { status: 503 });
  }
}

/**
 * Handle other HTTP methods
 */
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, x-webhook-signature',
    },
  });
}
