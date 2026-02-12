import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.API_INTERNAL_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  const lang = request.nextUrl.searchParams.get('lang') || 'ja'
  const body = await request.text()
  const token = request.headers.get('authorization') || ''

  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 120_000) // 120s timeout

    const res = await fetch(
      `${BACKEND_URL}/api/v1/struct-code/consultation?lang=${lang}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: token } : {}),
        },
        body,
        signal: controller.signal,
      }
    )

    clearTimeout(timeout)

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    if (e.name === 'AbortError') {
      return NextResponse.json(
        { detail: 'Consultation request timed out' },
        { status: 504 }
      )
    }
    return NextResponse.json(
      { detail: 'Consultation service unavailable' },
      { status: 502 }
    )
  }
}
