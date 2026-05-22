// ReactBits-style "Threads" background — powered by ogl (WebGL).
// Minimal animated black/white line field. `color` is RGB in 0..1.
import { useEffect, useRef } from "react";
import { Renderer, Program, Mesh, Triangle } from "ogl";

const VERT = /* glsl */ `
  attribute vec2 position;
  void main() { gl_Position = vec4(position, 0.0, 1.0); }
`;

const FRAG = /* glsl */ `
  precision highp float;
  uniform float uTime;
  uniform vec2 uResolution;
  uniform vec3 uColor;
  uniform float uAmplitude;
  uniform float uDistance;

  #define LINES 36

  void main() {
    vec2 uv = gl_FragCoord.xy / uResolution.xy;
    float intensity = 0.0;
    for (int i = 0; i < LINES; i++) {
      float fi = float(i);
      float t = uTime * (0.18 + fi * 0.006);
      float base = (fi - float(LINES) * 0.5) * uDistance;
      float y = 0.5 + base
        + sin(uv.x * 6.2831 + t + fi * 0.35) * 0.10 * uAmplitude
        + sin(uv.x * 12.566 - t * 0.7 + fi) * 0.035 * uAmplitude;
      float d = abs(uv.y - y);
      intensity += smoothstep(0.0024, 0.0, d);
    }
    intensity = clamp(intensity, 0.0, 1.0);
    // soft vertical fade so it reads as a backdrop, not a chart
    float fade = smoothstep(0.0, 0.35, uv.y) * smoothstep(1.0, 0.65, uv.y);
    gl_FragColor = vec4(uColor, intensity * 0.55 * mix(0.5, 1.0, fade));
  }
`;

export function Threads({
  color = [1, 1, 1],
  amplitude = 1,
  distance = 0.0,
  className,
}: {
  color?: [number, number, number];
  amplitude?: number;
  distance?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container) return;

    const renderer = new Renderer({ alpha: true, antialias: true });
    const gl = renderer.gl;
    gl.clearColor(0, 0, 0, 0);
    container.appendChild(gl.canvas);

    const program = new Program(gl, {
      vertex: VERT,
      fragment: FRAG,
      transparent: true,
      uniforms: {
        uTime: { value: 0 },
        uResolution: { value: [1, 1] },
        uColor: { value: color },
        uAmplitude: { value: amplitude },
        uDistance: { value: distance },
      },
    });
    const mesh = new Mesh(gl, { geometry: new Triangle(gl), program });

    const resize = () => {
      const { clientWidth: w, clientHeight: h } = container;
      renderer.setSize(w, h);
      program.uniforms.uResolution.value = [
        gl.canvas.width,
        gl.canvas.height,
      ];
    };
    window.addEventListener("resize", resize);
    resize();

    let raf = 0;
    const start = performance.now();
    const loop = (now: number) => {
      program.uniforms.uTime.value = (now - start) / 1000;
      program.uniforms.uColor.value = color;
      renderer.render({ scene: mesh });
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      if (gl.canvas.parentNode === container)
        container.removeChild(gl.canvas);
      gl.getExtension("WEBGL_lose_context")?.loseContext();
    };
    // color is read each frame from the ref-captured closure; re-run on change
  }, [color, amplitude, distance]);

  return (
    <div
      ref={ref}
      className={className}
      style={{ position: "absolute", inset: 0 }}
      aria-hidden
    />
  );
}
