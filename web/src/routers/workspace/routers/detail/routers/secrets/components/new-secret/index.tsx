import { PlusOutlined } from "@ant-design/icons";
import { SecretForm } from "@lepton-dashboard/routers/workspace/routers/detail/routers/secrets/components/secret-form";
import { Button, Modal } from "antd";
import { FC, useState } from "react";

export const NewSecret: FC<{ afterAction: () => void }> = ({ afterAction }) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        size="small"
        type="primary"
        icon={<PlusOutlined />}
        onClick={() => setOpen(true)}
      >
        New secret
      </Button>
      <Modal
        destroyOnClose={true}
        open={open}
        footer={null}
        title="New secret"
        onCancel={() => setOpen(false)}
      >
        <SecretForm
          finish={() => {
            afterAction();
            setOpen(false);
          }}
        />
      </Modal>
    </>
  );
};
