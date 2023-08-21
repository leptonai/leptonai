import { FC, useEffect, useRef } from "react";

export const Stopwatch: FC<{ start: boolean }> = ({ start }) => {
  const elRef = useRef<HTMLSpanElement>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (start) {
      let time = 0;
      timerRef.current = window.setInterval(() => {
        time += 100;
        if (elRef.current) {
          elRef.current.innerText = `${(time / 1000).toFixed(2)}s`;
        }
      }, 100);
    } else {
      if (elRef.current) {
        elRef.current.innerText = "";
      }
    }
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [start]);

  return <span ref={elRef} />;
};
