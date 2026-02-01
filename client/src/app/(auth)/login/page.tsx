"use client";

import { LoginForm } from "@/components/auth/LoginForm";
import PixelBlast from "@/components/PixelBlast";

export default function LoginPage() {
  return (
    <div className="relative flex min-h-[calc(100vh-4rem)] w-full flex-col lg:flex-row">
      {/* Left: PixelBlast background (inspired by bayer-dithering-webgl-demo) */}
      <div className="relative h-[320px] w-full shrink-0 lg:h-[calc(100vh-4rem)] lg:w-[55%]">
        <PixelBlast
          variant="square"
          pixelSize={4}
          color="#B19EEF"
          patternScale={2}
          patternDensity={1}
          pixelSizeJitter={0}
          enableRipples
          rippleSpeed={0.4}
          rippleThickness={0.12}
          rippleIntensityScale={1.5}
          liquid={false}
          liquidStrength={0.12}
          liquidRadius={1.2}
          liquidWobbleSpeed={5}
          speed={0.5}
          edgeFade={0.25}
          transparent
          className="absolute inset-0"
        />
      </div>

      {/* Right: Dark form panel */}
      <div className="flex flex-1 flex-col justify-center bg-zinc-950 px-6 py-12 lg:px-12 lg:py-16">
        <div className="mx-auto w-full max-w-[400px] text-center">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            Please log in to continue.
          </p>
          <div className="mt-8">
            <LoginForm />
          </div>
        </div>
      </div>
    </div>
  );
}
