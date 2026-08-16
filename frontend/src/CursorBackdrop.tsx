import { useEffect, useRef } from 'react'

type Particle = {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  a: number
}

/**
 * Full-viewport ambient layer: soft spotlight + drifting particles that react to the cursor.
 * pointer-events: none so dashboard controls stay fully usable.
 */
export function CursorBackdrop() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouse = useRef({ x: 0.5, y: 0.35, tx: 0.5, ty: 0.35 })
  const reduced = useRef(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    reduced.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let width = 0
    let height = 0
    let raf = 0
    const particles: Particle[] = []

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = window.innerWidth
      height = window.innerHeight
      canvas!.width = Math.floor(width * dpr)
      canvas!.height = Math.floor(height * dpr)
      canvas!.style.width = `${width}px`
      canvas!.style.height = `${height}px`
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)

      const count = Math.min(90, Math.floor((width * height) / 18000))
      particles.length = 0
      for (let i = 0; i < count; i++) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35,
          r: 1 + Math.random() * 2.2,
          a: 0.15 + Math.random() * 0.45,
        })
      }
    }

    function onMove(e: PointerEvent) {
      mouse.current.tx = e.clientX / Math.max(width, 1)
      mouse.current.ty = e.clientY / Math.max(height, 1)
      document.documentElement.style.setProperty('--cursor-x', `${e.clientX}px`)
      document.documentElement.style.setProperty('--cursor-y', `${e.clientY}px`)
    }

    function tick() {
      const m = mouse.current
      m.x += (m.tx - m.x) * 0.08
      m.y += (m.ty - m.y) * 0.08

      const mx = m.x * width
      const my = m.y * height

      ctx!.clearRect(0, 0, width, height)

      // Deep base
      ctx!.fillStyle = '#010409'
      ctx!.fillRect(0, 0, width, height)

      // Cursor spotlight (Antigravity-style reactive wash)
      const glow = ctx!.createRadialGradient(mx, my, 0, mx, my, Math.max(width, height) * 0.45)
      glow.addColorStop(0, 'rgba(56, 139, 253, 0.22)')
      glow.addColorStop(0.35, 'rgba(46, 160, 67, 0.08)')
      glow.addColorStop(1, 'rgba(1, 4, 9, 0)')
      ctx!.fillStyle = glow
      ctx!.fillRect(0, 0, width, height)

      // Secondary ambient blob opposite cursor
      const ox = width * (1 - m.x)
      const oy = height * (1 - m.y)
      const ambient = ctx!.createRadialGradient(ox, oy, 0, ox, oy, Math.max(width, height) * 0.4)
      ambient.addColorStop(0, 'rgba(163, 113, 247, 0.07)')
      ambient.addColorStop(1, 'rgba(1, 4, 9, 0)')
      ctx!.fillStyle = ambient
      ctx!.fillRect(0, 0, width, height)

      // Soft grid that brightens near cursor
      ctx!.strokeStyle = 'rgba(48, 54, 61, 0.55)'
      ctx!.lineWidth = 1
      const step = 56
      for (let x = 0; x < width; x += step) {
        ctx!.beginPath()
        ctx!.moveTo(x, 0)
        ctx!.lineTo(x, height)
        ctx!.stroke()
      }
      for (let y = 0; y < height; y += step) {
        ctx!.beginPath()
        ctx!.moveTo(0, y)
        ctx!.lineTo(width, y)
        ctx!.stroke()
      }

      if (!reduced.current) {
        for (const p of particles) {
          const dx = mx - p.x
          const dy = my - p.y
          const dist = Math.hypot(dx, dy) || 1
          // Gentle attract within radius; slight scatter when very close
          if (dist < 220) {
            const force = ((220 - dist) / 220) * 0.045
            p.vx += (dx / dist) * force
            p.vy += (dy / dist) * force
          }
          if (dist < 70) {
            p.vx -= (dx / dist) * 0.08
            p.vy -= (dy / dist) * 0.08
          }

          p.vx *= 0.97
          p.vy *= 0.97
          p.x += p.vx
          p.y += p.vy

          if (p.x < -10) p.x = width + 10
          if (p.x > width + 10) p.x = -10
          if (p.y < -10) p.y = height + 10
          if (p.y > height + 10) p.y = -10

          const near = Math.max(0, 1 - dist / 280)
          ctx!.beginPath()
          ctx!.fillStyle = `rgba(110, 168, 254, ${p.a + near * 0.45})`
          ctx!.arc(p.x, p.y, p.r + near * 1.5, 0, Math.PI * 2)
          ctx!.fill()
        }

        // Connection lines near cursor (subtle constellation)
        ctx!.lineWidth = 1
        for (let i = 0; i < particles.length; i++) {
          const a = particles[i]
          const da = Math.hypot(a.x - mx, a.y - my)
          if (da > 160) continue
          for (let j = i + 1; j < particles.length; j++) {
            const b = particles[j]
            const d = Math.hypot(a.x - b.x, a.y - b.y)
            if (d > 90) continue
            const alpha = (1 - d / 90) * 0.25
            ctx!.strokeStyle = `rgba(88, 166, 255, ${alpha})`
            ctx!.beginPath()
            ctx!.moveTo(a.x, a.y)
            ctx!.lineTo(b.x, b.y)
            ctx!.stroke()
          }
        }
      }

      raf = requestAnimationFrame(tick)
    }

    resize()
    mouse.current.x = 0.5
    mouse.current.y = 0.35
    mouse.current.tx = 0.5
    mouse.current.ty = 0.35
    window.addEventListener('resize', resize)
    window.addEventListener('pointermove', onMove, { passive: true })
    raf = requestAnimationFrame(tick)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      window.removeEventListener('pointermove', onMove)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className="pointer-events-none fixed inset-0 z-0"
    />
  )
}
