import { FC, PropsWithChildren } from "react";
import { Card } from "@lepton-dashboard/components/card";

export const BreadcrumbHeader: FC<PropsWithChildren> = ({ children }) => {
  return <Card>{children}</Card>;
};
