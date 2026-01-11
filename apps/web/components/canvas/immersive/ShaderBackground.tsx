"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// GLSL Shader for procedural nebula effect
const VERTEX_SHADER = `#version 300 es
in vec4 a_position;
void main() {
  gl_Position = a_position;
}`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_mouse;
uniform vec3 u_colorPrimary;
uniform vec3 u_colorSecondary;
uniform float u_intensity;

out vec4 fragColor;

// Simplex 2D noise
vec3 permute(vec3 x) { return mod(((x*34.0)+1.0)*x, 289.0); }

float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439,
           -0.577350269189626, 0.024390243902439);
  vec2 i  = floor(v + dot(v, C.yy));
  vec2 x0 = v -   i + dot(i, C.xx);
  vec2 i1;
  i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
    + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
    dot(x12.zw,x12.zw)), 0.0);
  m = m*m;
  m = m*m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}

// Fractal Brownian Motion
float fbm(vec2 p) {
  float value = 0.0;
  float amplitude = 0.5;
  float frequency = 1.0;
  for (int i = 0; i < 6; i++) {
    value += amplitude * snoise(p * frequency);
    amplitude *= 0.5;
    frequency *= 2.0;
  }
  return value;
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  vec2 aspect = vec2(u_resolution.x / u_resolution.y, 1.0);

  // Mouse parallax (subtle)
  vec2 mouse = (u_mouse - 0.5) * 0.02;
  uv += mouse;

  // Animated noise coordinates
  float time = u_time * 0.05;
  vec2 p = uv * aspect * 2.0;

  // Multiple noise layers for nebula effect
  float n1 = fbm(p + time);
  float n2 = fbm(p * 1.5 - time * 0.7 + vec2(5.0, 3.0));
  float n3 = fbm(p * 0.5 + time * 0.3 + vec2(n1, n2));

  // Combine noise layers
  float nebula = n1 * 0.4 + n2 * 0.3 + n3 * 0.3;
  nebula = smoothstep(-0.3, 0.8, nebula);

  // Color gradient
  vec3 color1 = u_colorPrimary;
  vec3 color2 = u_colorSecondary;
  vec3 nebulaColor = mix(color1, color2, nebula);

  // Apply intensity with minimum brightness
  float brightness = mix(0.3, 1.0, nebula); // Ensure minimum brightness
  nebulaColor *= brightness * u_intensity;

  // Add subtle star field
  float stars = 0.0;
  vec2 starUv = uv * 100.0;
  float starNoise = snoise(starUv);
  if (starNoise > 0.97) {
    float twinkle = sin(u_time * 3.0 + starNoise * 100.0) * 0.5 + 0.5;
    stars = pow(starNoise - 0.97, 2.0) * 300.0 * twinkle;
  }

  // Combine nebula and stars
  vec3 finalColor = nebulaColor + vec3(stars);

  // Vignette
  float vignette = 1.0 - length((uv - 0.5) * 1.2);
  vignette = smoothstep(0.0, 1.0, vignette);
  finalColor *= vignette;

  fragColor = vec4(finalColor, 1.0);
}`;

interface ShaderBackgroundProps {
  colorPrimary?: [number, number, number];
  colorSecondary?: [number, number, number];
  intensity?: number;
  className?: string;
}

export function ShaderBackground({
  colorPrimary = [0.0, 0.6, 0.5], // Bright teal
  colorSecondary = [0.3, 0.0, 0.5], // Bright purple
  intensity = 1.2, // Higher intensity for visibility
  className = "",
}: ShaderBackgroundProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glRef = useRef<WebGL2RenderingContext | null>(null);
  const programRef = useRef<WebGLProgram | null>(null);
  const animationRef = useRef<number>(0);
  const mouseRef = useRef({ x: 0.5, y: 0.5 });
  const startTimeRef = useRef(Date.now());
  const [isSupported, setIsSupported] = useState(true);

  // Check for reduced motion preference
  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  const initShader = useCallback(
    (gl: WebGL2RenderingContext, type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;

      gl.shaderSource(shader, source);
      gl.compileShader(shader);

      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error("Shader compile error:", gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }

      return shader;
    },
    []
  );

  const initWebGL = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return false;

    const gl = canvas.getContext("webgl2", {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      preserveDrawingBuffer: false,
    });

    if (!gl) {
      console.warn("WebGL2 not supported");
      setIsSupported(false);
      return false;
    }

    glRef.current = gl;

    // Create shaders
    const vertexShader = initShader(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
    const fragmentShader = initShader(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);

    if (!vertexShader || !fragmentShader) {
      setIsSupported(false);
      return false;
    }

    // Create program
    const program = gl.createProgram();
    if (!program) return false;

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Program link error:", gl.getProgramInfoLog(program));
      return false;
    }

    programRef.current = program;

    // Create full-screen quad
    const positions = new Float32Array([
      -1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1,
    ]);

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

    const positionLoc = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(positionLoc);
    gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

    return true;
  }, [initShader]);

  const render = useCallback(() => {
    const gl = glRef.current;
    const program = programRef.current;
    const canvas = canvasRef.current;

    if (!gl || !program || !canvas) return;

    // Resize if needed
    if (
      canvas.width !== canvas.clientWidth ||
      canvas.height !== canvas.clientHeight
    ) {
      canvas.width = canvas.clientWidth;
      canvas.height = canvas.clientHeight;
      gl.viewport(0, 0, canvas.width, canvas.height);
    }

    gl.useProgram(program);

    // Set uniforms
    const time = (Date.now() - startTimeRef.current) / 1000;
    gl.uniform1f(gl.getUniformLocation(program, "u_time"), time);
    gl.uniform2f(
      gl.getUniformLocation(program, "u_resolution"),
      canvas.width,
      canvas.height
    );
    gl.uniform2f(
      gl.getUniformLocation(program, "u_mouse"),
      mouseRef.current.x,
      mouseRef.current.y
    );
    gl.uniform3f(
      gl.getUniformLocation(program, "u_colorPrimary"),
      ...colorPrimary
    );
    gl.uniform3f(
      gl.getUniformLocation(program, "u_colorSecondary"),
      ...colorSecondary
    );
    gl.uniform1f(gl.getUniformLocation(program, "u_intensity"), intensity);

    gl.drawArrays(gl.TRIANGLES, 0, 6);

    if (!prefersReducedMotion) {
      animationRef.current = requestAnimationFrame(render);
    }
  }, [colorPrimary, colorSecondary, intensity, prefersReducedMotion]);

  useEffect(() => {
    if (!initWebGL()) return;

    // Mouse tracking
    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current = {
        x: e.clientX / window.innerWidth,
        y: 1 - e.clientY / window.innerHeight,
      };
    };

    window.addEventListener("mousemove", handleMouseMove);

    // Start animation
    if (prefersReducedMotion) {
      // Render once for reduced motion
      render();
    } else {
      animationRef.current = requestAnimationFrame(render);
    }

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(animationRef.current);

      // Cleanup WebGL
      const gl = glRef.current;
      const program = programRef.current;
      if (gl && program) {
        gl.deleteProgram(program);
      }
    };
  }, [initWebGL, render, prefersReducedMotion]);

  const baseStyle: React.CSSProperties = {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: "100%",
    height: "100%",
    pointerEvents: "none",
    zIndex: 0,
  };

  if (!isSupported) {
    // Fallback gradient
    return (
      <div
        className={className}
        style={{
          ...baseStyle,
          background: `radial-gradient(ellipse at center,
            rgba(${colorPrimary.map((c) => Math.round(c * 255)).join(",")}, 0.3) 0%,
            rgba(${colorSecondary.map((c) => Math.round(c * 255)).join(",")}, 0.2) 50%,
            #000 100%)`,
        }}
      />
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={baseStyle}
    />
  );
}

export default ShaderBackground;
