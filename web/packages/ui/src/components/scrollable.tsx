import {
  forwardRef,
  PropsWithChildren,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import type { BaseHTMLAttributes } from "react";
import { css } from "@emotion/react";

export type ScrollablePosition = "start" | "end";

export interface ScrollableProps extends BaseHTMLAttributes<HTMLDivElement> {
  position?: "start" | "end" | ["start", "end"];
  margin?: string;
}

export interface ScrollableRef {
  scrollToBottom: () => void;
}

export const Scrollable = forwardRef<
  ScrollableRef,
  PropsWithChildren<ScrollableProps>
>(({ position = "start", className, children, margin, ...props }, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollableBoxRef = useRef<HTMLDivElement | null>(null);
  const [positions, setPositions] = useState<ScrollablePosition[]>([]);
  const scrollHTMLRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    setPositions(Array.isArray(position) ? position : [position]);
  }, [position]);

  useImperativeHandle(
    ref,
    () => ({
      scrollToBottom: () => {
        scrollHTMLRef.current?.scrollTo({
          top: scrollHTMLRef.current.scrollHeight,
          behavior: "smooth",
        });
      },
    }),
    []
  );

  useEffect(() => {
    const container = containerRef.current;
    const scrollableBox = scrollableBoxRef.current;
    if (!container || !scrollableBox) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const target = entry.target as HTMLElement;
          const positionData = target.dataset.position as ScrollablePosition;
          if (!positionData) return;
          if (positions.includes(positionData) && entry.intersectionRatio < 1) {
            container.classList.add(`scrollable-${positionData}`);
          } else {
            container.classList.remove(`scrollable-${positionData}`);
          }
        });
      },
      {
        root: scrollableBox,
        threshold: [0, 1],
        rootMargin: margin,
      }
    );

    observer.observe(scrollableBox.firstElementChild as HTMLElement);
    observer.observe(scrollableBox.lastElementChild as HTMLElement);
    return () => observer.disconnect();
  }, [margin, positions]);

  return (
    <div
      css={css`
        position: relative;
        display: flex;
        overflow: hidden;
        height: auto;
        width: auto;

        & > .scrollable-container {
          flex: 1;
          overflow: auto;
        }

        &::before,
        &::after {
          content: "";
          display: block;
          opacity: 0;
          transition: opacity 0.3s ease-in-out;
          position: absolute;
          z-index: 1;
        }

        &.scrollable-start::before {
          opacity: 1;
          top: 0;
          left: 0;
          right: 0;
          box-shadow: 0 1px 8px 2px hsl(var(--border));
        }

        &.scrollable-end::after {
          opacity: 1;
          bottom: 0;
          left: 0;
          right: 0;
          box-shadow: 0 -1px 8px 2px hsl(var(--border));
        }
      `}
      ref={containerRef}
      className={className}
      {...props}
    >
      <div
        ref={(ref) => {
          if (scrollHTMLRef) {
            scrollHTMLRef.current = ref;
          }
          scrollableBoxRef.current = ref;
        }}
        className="scrollable-container"
      >
        <span data-position="start" />
        {children}
        <span data-position="end" />
      </div>
    </div>
  );
});

Scrollable.displayName = "Scrollable";
