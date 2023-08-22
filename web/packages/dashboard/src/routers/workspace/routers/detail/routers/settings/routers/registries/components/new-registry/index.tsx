import { PlusOutlined } from "@ant-design/icons";
import { Button, Modal } from "antd";
import { FC, useState } from "react";
import { RegistryForm } from "../registry-form";

export const NewRegistry: FC<{ afterAction: () => void }> = ({
  afterAction,
}) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        size="small"
        type="primary"
        icon={<PlusOutlined />}
        onClick={() => setOpen(true)}
      >
        New registry
      </Button>
      <Modal
        destroyOnClose={true}
        open={open}
        footer={null}
        title="New registry"
        onCancel={() => setOpen(false)}
      >
        <RegistryForm
          finish={() => {
            afterAction();
            setOpen(false);
          }}
        />
      </Modal>
    </>
  );
};
