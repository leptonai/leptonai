import { FC, PropsWithChildren, useEffect, useState } from "react";

export const Delay: FC<PropsWithChildren<{ delay: number }>> = ({
  delay,
  children,
}) => {
  const [show, setShow] = useState(false);
  useEffect(() => {
    const timeout = setTimeout(() => setShow(true), delay);
    return () => clearTimeout(timeout);
  }, [delay]);
  return show ? <>{children}</> : null;
};
