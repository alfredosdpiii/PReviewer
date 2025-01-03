import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    console.log('Received stream request with body:', body)

    const response = await fetch('http://localhost:8000/api/review/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),  // Forward the exact same body
    })

    if (!response.ok) {
      const error = await response.text()
      console.error('FastAPI error:', error)
      return NextResponse.json({ 
        success: false, 
        error: error,
      }, { status: response.status })
    }

    // Forward the stream from the FastAPI server
    const stream = new ReadableStream({
      async start(controller) {
        const reader = response.body?.getReader()
        if (!reader) {
          controller.close()
          return
        }

        try {
          while (true) {
            const { done, value } = await reader.read()
            if (done) {
              break
            }
            controller.enqueue(value)
          }
        } finally {
          reader.releaseLock()
          controller.close()
        }
      }
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    })
  } catch (error) {
    console.error('Error processing PR:', error)
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    }, { status: 500 })
  }
}
