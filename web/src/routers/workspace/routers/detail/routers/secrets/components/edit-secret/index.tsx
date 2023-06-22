import { Edit as EditIcon } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Secret } from "@lepton-dashboard/interfaces/secret";
import { SecretForm } from "@lepton-dashboard/routers/workspace/routers/detail/routers/secrets/components/secret-form";
import { Button, Modal } from "antd";
import { FC, useState } from "react";

export const EditSecret: FC<{ afterAction: () => void; secret: Secret }> = ({
  afterAction,
  secret,
}) => {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        size="small"
        type="text"
        icon={<CarbonIcon icon={<EditIcon />} />}
        onClick={() => setOpen(true)}
      >
        Edit
      </Button>
      <Modal
        destroyOnClose={true}
        open={open}
        footer={null}
        title="Edit secret"
        onCancel={() => setOpen(false)}
      >
        <SecretForm
          initialValues={secret}
          edit
          finish={() => {
            afterAction();
            setOpen(false);
          }}
        />
      </Modal>
    </>
  );
};
