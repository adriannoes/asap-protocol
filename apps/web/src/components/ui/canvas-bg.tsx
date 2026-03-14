"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  useRef,
  useMemo,
  useEffect,
  Component,
  type ReactNode,
} from "react";
import type { ShaderMaterial as ShaderMaterialType } from "three";
import { cn } from "@/lib/utils";
import { useCanvasVisibility } from "@/hooks/use-canvas-visibility";
import { useIsMobile } from "@/hooks/use-mobile";

const VERTEX_SHADER = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const FRAGMENT_SHADER = `
  uniform float uTime;
  uniform vec3 uColor1;
  uniform vec3 uColor2;
  varying vec2 vUv;

  void main() {
    vec2 grid = fract(vUv * 12.0);
    float dist = length(grid - 0.5);
    float dot = smoothstep(0.25, 0.18, dist);
    vec3 color = mix(uColor1, uColor2, sin(uTime * 0.3 + vUv.x * 2.0) * 0.5 + 0.5);
    float alpha = dot * 0.12;
    gl_FragColor = vec4(color, alpha);
  }
`;

const COLOR_SCHEMES = {
  indigo: {
    color1: [0.28, 0.28, 0.32] as [number, number, number],
    color2: [0.39, 0.4, 0.95] as [number, number, number],
  },
  zinc: {
    color1: [0.2, 0.2, 0.22] as [number, number, number],
    color2: [0.35, 0.35, 0.4] as [number, number, number],
  },
};

interface DotMatrixSceneProps {
  colorScheme: "indigo" | "zinc";
  isVisible: boolean;
}

function DotMatrixScene({ colorScheme, isVisible }: DotMatrixSceneProps) {
  const materialRef = useRef<ShaderMaterialType>(null);
  const { invalidate } = useThree();

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uColor1: { value: COLOR_SCHEMES[colorScheme].color1 },
      uColor2: { value: COLOR_SCHEMES[colorScheme].color2 },
    }),
    [colorScheme]
  );

  useEffect(() => {
    if (isVisible) invalidate();
  }, [isVisible, invalidate]);

  useFrame((_, delta) => {
    if (!isVisible) return;

    // Unconditionally request the next frame while visible.
    // Keeps the 'demand' loop alive (required for frameloop="demand").
    invalidate();

    if (!materialRef.current) return;
    materialRef.current.uniforms.uTime.value += delta;
  });

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        attach="material"
        uniforms={uniforms}
        vertexShader={VERTEX_SHADER}
        fragmentShader={FRAGMENT_SHADER}
        transparent
        depthWrite={false}
      />
    </mesh>
  );
}

const FALLBACK_GRADIENT =
  "absolute inset-0 -z-10 bg-gradient-to-br from-zinc-950 via-indigo-950/20 to-zinc-950";

interface WebGLErrorBoundaryProps {
  className?: string;
  children: ReactNode;
}

class WebGLErrorBoundary extends Component<
  WebGLErrorBoundaryProps,
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError = () => ({ hasError: true });

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          className={cn(FALLBACK_GRADIENT, this.props.className)}
          data-testid="canvas-bg"
        />
      );
    }
    return this.props.children;
  }
}

export interface CanvasBgProps {
  className?: string;
  colorScheme?: "indigo" | "zinc";
}

export function CanvasBg({
  className,
  colorScheme = "indigo",
}: CanvasBgProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isVisible = useCanvasVisibility(containerRef);
  const isMobile = useIsMobile();
  const dpr: [number, number] = isMobile ? [1, 1] : [1, 1.5];

  return (
    <WebGLErrorBoundary className={className}>
      <div
        ref={containerRef}
        className={cn("absolute inset-0 -z-10", className)}
        data-testid="canvas-bg"
      >
        <Canvas
          frameloop="demand"
          dpr={dpr}
          gl={{ antialias: false, alpha: true }}
        >
          <DotMatrixScene colorScheme={colorScheme} isVisible={isVisible} />
        </Canvas>
      </div>
    </WebGLErrorBoundary>
  );
}
