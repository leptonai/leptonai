import { Code } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { ChatAPIModal } from "@lepton-libs/gradio/chat-api-modal";
import { Button, Grid } from "antd";
import { FC, useState } from "react";

export const Api: FC<{ apiUrl: string; title: string }> = ({
  apiUrl,
  title,
}) => {
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
        {md !== false ? title : null}
      </Button>
      <ChatAPIModal
        apiUrl={apiUrl}
        open={open}
        setOpen={setOpen}
        title="Llama API"
      />
    </>
  );
};
