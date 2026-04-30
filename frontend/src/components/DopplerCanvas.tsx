import { useEffect, useRef } from "react";

// CS2 多普勒七彩 WebGL 着色器（与 preview.html 同款 GLSL）
const VS = `
attribute vec2 a_position;
varying vec2 v_uv;
void main() {
  v_uv = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

const FS = `
precision highp float;
uniform float u_time;
uniform vec2  u_resolution;
varying vec2  v_uv;

vec2 hash(vec2 p) {
  p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
}
float noise(vec2 p) {
  const float K1 = 0.366025404;
  const float K2 = 0.211324865;
  vec2 i = floor(p + (p.x + p.y) * K1);
  vec2 a = p - i + (i.x + i.y) * K2;
  vec2 o = (a.x > a.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec2 b = a - o + K2;
  vec2 c = a - 1.0 + 2.0 * K2;
  vec3 h = max(0.5 - vec3(dot(a,a), dot(b,b), dot(c,c)), 0.0);
  vec3 n = h*h*h*h * vec3(dot(a, hash(i)), dot(b, hash(i+o)), dot(c, hash(i+1.0)));
  return dot(n, vec3(70.0));
}

void main() {
  vec2 uv = v_uv;
  vec2 p  = (uv - 0.5) * vec2(u_resolution.x / u_resolution.y, 1.0);
  float t = u_time * 0.08;

  float n = 0.0;
  n += noise(p * 1.5 + vec2(t * 0.6, 0.0)) * 0.6;
  n += noise(p * 3.0 - vec2(0.0, t * 0.4)) * 0.3;
  n += noise(p * 6.0 + vec2(t * 0.2, t * 0.3)) * 0.1;

  float dist = length(p);
  float falloff = smoothstep(1.0, 0.2, dist);

  vec3 c1 = vec3(1.0,   0.235, 0.675);
  vec3 c2 = vec3(0.471, 0.294, 0.627);
  vec3 c3 = vec3(0.169, 0.525, 0.773);
  vec3 c4 = vec3(0.0,   0.788, 1.0);
  vec3 c5 = vec3(0.961, 0.620, 0.043);

  float pos = n * 0.5 + 0.5;
  vec3 col;
  if (pos < 0.25) {
    col = mix(c1, c2, pos * 4.0);
  } else if (pos < 0.5) {
    col = mix(c2, c3, (pos - 0.25) * 4.0);
  } else if (pos < 0.75) {
    col = mix(c3, c4, (pos - 0.5) * 4.0);
  } else {
    col = mix(c4, c5, (pos - 0.75) * 4.0);
  }

  col = mix(vec3(1.0), col, falloff * 0.9);
  gl_FragColor = vec4(col, 1.0);
}
`;

function compileShader(gl: WebGLRenderingContext, src: string, type: number): WebGLShader | null {
  const sh = gl.createShader(type);
  if (!sh) return null;
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    console.error("Shader error:", gl.getShaderInfoLog(sh));
    gl.deleteShader(sh);
    return null;
  }
  return sh;
}

export default function DopplerCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", { antialias: false, premultipliedAlpha: false });
    if (!gl) return; // 静默降级：老浏览器无 WebGL

    const vs = compileShader(gl, VS, gl.VERTEX_SHADER);
    const fs = compileShader(gl, FS, gl.FRAGMENT_SHADER);
    if (!vs || !fs) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Program link error:", gl.getProgramInfoLog(program));
      return;
    }
    gl.useProgram(program);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW
    );
    const posLoc = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

    const uTime = gl.getUniformLocation(program, "u_time");
    const uRes = gl.getUniformLocation(program, "u_resolution");

    // capture non-null locals so TS can narrow inside the rAF closure
    const cv = canvas;
    const ctx = gl;

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = cv.clientWidth * dpr;
      const h = cv.clientHeight * dpr;
      if (cv.width !== w || cv.height !== h) {
        cv.width = w;
        cv.height = h;
        ctx.viewport(0, 0, w, h);
      }
    }

    let raf = 0;
    let alive = true;
    const startT = performance.now();
    function frame() {
      if (!alive) return;
      resize();
      const t = (performance.now() - startT) / 1000;
      ctx.uniform1f(uTime, t);
      ctx.uniform2f(uRes, cv.width, cv.height);
      ctx.drawArrays(ctx.TRIANGLE_STRIP, 0, 4);
      raf = requestAnimationFrame(frame);
    }
    frame();

    return () => {
      alive = false;
      cancelAnimationFrame(raf);
      gl.deleteProgram(program);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
      gl.deleteBuffer(buffer);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.55, mixBlendMode: "multiply" }}
    />
  );
}
