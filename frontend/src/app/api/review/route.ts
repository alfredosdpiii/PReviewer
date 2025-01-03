import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { pr_url } = await request.json()

    const response = await fetch('http://localhost:8000/api/review', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ pr_url }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to process PR')
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error processing PR:', error)
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error occurred',
      steps: [],
      report: null
    }, { status: 500 })
  }
}
