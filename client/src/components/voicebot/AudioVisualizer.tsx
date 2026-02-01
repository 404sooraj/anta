"use client";

import { useEffect, useRef, useState } from "react";

interface AudioVisualizerProps {
  audioLevel: number; // 0 to 1
  isActive: boolean;
}

export function AudioVisualizer({
  audioLevel,
  isActive,
}: AudioVisualizerProps) {
  const barsCount = 5;
  const [barHeights, setBarHeights] = useState<number[]>(Array(barsCount).fill(12));
  const animationRef = useRef<number | null>(null);
  const audioLevelRef = useRef(audioLevel);

  // Keep ref in sync with prop
  useEffect(() => {
    audioLevelRef.current = audioLevel;
  }, [audioLevel]);

  useEffect(() => {
    if (!isActive) {
      setBarHeights(Array(barsCount).fill(12));
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      return;
    }

    const animate = () => {
      const now = Date.now();
      const level = audioLevelRef.current;
      
      const newHeights = Array.from({ length: barsCount }, (_, i) => {
        // Create wave-like variation for each bar
        const phase = (i - Math.floor(barsCount / 2)) * 0.4;
        const wave = Math.sin(now / 120 + phase);
        
        const minHeight = 12;
        const maxHeight = 48;
        
        // Combine audio level with wave pattern
        const levelContribution = level * (maxHeight - minHeight) * 0.9;
        const waveContribution = wave * 8 * Math.max(0.2, level);
        
        const height = minHeight + levelContribution + waveContribution;
        return Math.max(minHeight, Math.min(maxHeight, height));
      });
      
      setBarHeights(newHeights);
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, barsCount]);

  return (
    <div className="flex items-center justify-center gap-1.5 h-12">
      {barHeights.map((height, i) => (
        <div
          key={i}
          className={`
            w-2 rounded-full transition-colors duration-200
            ${
              isActive
                ? "bg-gradient-to-t from-[#B19EEF] to-[#C4B4F5]"
                : "bg-zinc-300 dark:bg-zinc-700"
            }
          `}
          style={{
            height: `${height}px`,
            transition: 'height 50ms ease-out',
          }}
        />
      ))}
    </div>
  );
}

// Animated ring visualizer (alternative style)
export function RingVisualizer({ audioLevel, isActive }: AudioVisualizerProps) {
  const rings = 3;

  return (
    <div className="relative w-32 h-32 flex items-center justify-center">
      {Array.from({ length: rings }).map((_, i) => {
        const scale = 1 + i * 0.3 + (isActive ? audioLevel * 0.5 : 0);
        const opacity = isActive ? 0.3 - i * 0.1 : 0.1;

        return (
          <div
            key={i}
            className={`
              absolute inset-0 rounded-full border-2 transition-all duration-150
              ${isActive ? "border-[#B19EEF]" : "border-zinc-300 dark:border-zinc-700"}
            `}
            style={{
              transform: `scale(${scale})`,
              opacity,
            }}
          />
        );
      })}
    </div>
  );
}
