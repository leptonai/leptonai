import { Code } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { CodeAPIModal } from "@lepton-libs/gradio/code-api-modal";
import { Button, Grid } from "antd";
import { FC, useState } from "react";

export const Api: FC<{
  code: string;
  name: string;
}> = ({ code, name }) => {
  const { md } = Grid.useBreakpoint();
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        type="text"
        size="small"
        onClick={() => setOpen(true)}
        icon={<CarbonIcon icon={<Code />} />}
      >
        {md !== false ? "API" : null}
      </Button>
      <CodeAPIModal
        code={code}
        open={open}
        setOpen={setOpen}
        title={`Copy API for ${name}`}
      />
    </>
  );
};
