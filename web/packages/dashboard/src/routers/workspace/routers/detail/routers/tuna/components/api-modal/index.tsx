import { CodeAPIDialogContent } from "@lepton/playground/components/code-api-dialog";
import { Button, Tooltip } from "antd";
import { SizeType } from "antd/lib/config-provider/SizeContext";
import { FC, PropsWithChildren, ReactNode, useState } from "react";
import { APICodeTemplate } from "@lepton/playground/shared/api-code-template";

export interface ApiModalProps {
  name: string;
  size?: SizeType;
  apiUrl: string;
  apiKey?: string;
  disabled?: boolean;
  icon?: ReactNode;
}
export const ApiModal: FC<ApiModalProps & PropsWithChildren> = ({
  name,
  apiUrl,
  apiKey,
  size,
  disabled,
  icon,
  children,
}) => {
  const [open, setOpen] = useState(false);
  const codes = Object.entries(APICodeTemplate.chat(apiUrl, apiKey)).map(
    ([language, code]) => ({ language, code })
  );
  return (
    <>
      <Tooltip placement="top" title="Get code template for this tuna">
        <Button
          disabled={disabled}
          size={size}
          key="deploy"
          type="text"
          icon={icon}
          onClick={() => setOpen(true)}
        >
          {children}
        </Button>
      </Tooltip>

      <CodeAPIDialogContent
        title={`Copy API for ${name}`}
        codes={codes}
        maskString={apiKey}
        open={open}
        onOpenChange={setOpen}
      />
    </>
  );
};
