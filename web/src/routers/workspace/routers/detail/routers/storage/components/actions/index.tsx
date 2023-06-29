import { FC, useCallback, useRef, useState } from "react";
import {
  App,
  Button,
  Input,
  InputRef,
  Popconfirm,
  Space,
  Upload as AntdUpload,
} from "antd";
import { useInject } from "@lepton-libs/di";
import { DocumentAdd, FolderAdd, TrashCan } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { FileManagerService } from "@lepton-dashboard/routers/workspace/services/file-manager.service";
import { FileInfo } from "@lepton-dashboard/interfaces/storage";
import { css } from "@emotion/react";

export interface ActionsProps {
  path: string;
  selectedPath?: string;
  files: FileInfo[];
  refresh: () => void;
  disabled?: boolean;
}

export const Actions: FC<ActionsProps> = ({
  path,
  files,
  disabled,
  selectedPath,
  refresh,
}) => {
  const fileManagerService: FileManagerService<FileInfo> =
    useInject(FileManagerService);
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [addFolderLoading, setAddFolderLoading] = useState(false);
  const [isNewFolderPopOpen, setIsNewFolderPopOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const newFolderInputRef = useRef<InputRef | null>(null);

  const addNewFolderItem = useCallback(() => {
    let newFolderName = "New Folder";
    let i = 1;
    while (
      files.some(
        (file) =>
          file.name === (i > 1 ? `${newFolderName} (${i})` : newFolderName)
      )
    ) {
      i++;
    }
    if (i > 1) {
      newFolderName += ` (${i})`;
    }

    setNewFolderName(newFolderName);
    setIsNewFolderPopOpen(true);
  }, [files]);

  const validateFolderName = useCallback(
    (name: string) => {
      if (name === "") {
        return "Folder name cannot be empty";
      }
      if (files.some((file) => file.name === name)) {
        return "Folder name already exists";
      }

      /**
       * from [z/OS data set and UNIX file naming conventions](https://www.ibm.com/docs/en/zos/2.4.0?topic=pages-zos-data-set-unix-file-naming-conventions)
       * and zh, jp, ko, en
       */
      const regex =
        /^[\u4E00-\u9FFF\uac00-\ud7a3\u3040-\u30ffa-zA-Z0-9\s+\-=|~[\]()<>{}\\?,.!;:'"&%$#@^*_]+$/;
      if (!regex.test(name)) {
        return "Folder name contains invalid characters";
      }

      if (`${path}/${name}`.length > 1023) {
        return "Folder name is too long";
      }

      return true;
    },
    [files, path]
  );

  const addNewFolder = useCallback(() => {
    const validateResult = validateFolderName(newFolderName);
    if (validateResult !== true) {
      void message.error(validateResult);
      return;
    }

    setAddFolderLoading(true);
    fileManagerService
      .create({
        path: `${path}/${newFolderName}`,
        name: newFolderName,
        type: "dir",
      })
      .subscribe({
        next: () => {
          setIsNewFolderPopOpen(false);
          setAddFolderLoading(false);
          refresh();
        },
        error: () => {
          setIsNewFolderPopOpen(false);
          setAddFolderLoading(false);
        },
      });
  }, [
    validateFolderName,
    newFolderName,
    fileManagerService,
    path,
    message,
    refresh,
  ]);

  const focusNewFolderInput = useCallback(() => {
    newFolderInputRef.current?.focus();
    newFolderInputRef.current?.select();
  }, [newFolderInputRef]);

  const beforeUpload = (file: File) => {
    setLoading(true);
    fileManagerService
      .create(
        {
          path: `${path}/${file.name}`,
          name: file.name,
          type: "file",
        },
        file
      )
      .subscribe({
        next: () => {
          setLoading(false);
          void message.success("Upload file success");
          refresh();
        },
        error: () => {
          setLoading(false);
          refresh();
        },
      });
    return false;
  };

  const deleteSelected = useCallback(() => {
    const exist = files.find((file) => file.path === selectedPath);
    if (!exist) {
      return;
    }

    fileManagerService.remove(exist).subscribe({
      next: () => {
        refresh();
      },
      error: () => {
        refresh();
      },
    });
  }, [selectedPath, fileManagerService, refresh, files]);
  return (
    <>
      <Space
        css={css`
          @media (max-width: 768px) {
            button > span:nth-of-type(2) {
              display: none;
            }
          }
        `}
      >
        <Popconfirm
          icon={null}
          disabled={disabled}
          title="Input new folder name"
          open={isNewFolderPopOpen}
          description={
            <Input
              css={css`
                margin-left: -13px;
              `}
              size="small"
              value={newFolderName}
              ref={newFolderInputRef}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  addNewFolder();
                }
                if (e.key === "Escape") {
                  setIsNewFolderPopOpen(false);
                }
              }}
            />
          }
          placement="bottomRight"
          okText="Create"
          okButtonProps={{ type: "primary", loading: addFolderLoading }}
          cancelText="Cancel"
          onCancel={() => setIsNewFolderPopOpen(false)}
          onOpenChange={(open) => {
            if (!open) {
              setIsNewFolderPopOpen(false);
            }
          }}
          onConfirm={addNewFolder}
          afterOpenChange={focusNewFolderInput}
        >
          <Button
            disabled={disabled}
            size="small"
            type="text"
            icon={<CarbonIcon icon={<FolderAdd />} />}
            onClick={addNewFolderItem}
          >
            Add Folder
          </Button>
        </Popconfirm>
        <AntdUpload
          disabled={disabled}
          fileList={[]}
          beforeUpload={beforeUpload}
          style={{ width: "100%" }}
        >
          <Button
            size="small"
            type="text"
            disabled={disabled}
            icon={<CarbonIcon icon={<DocumentAdd />} />}
            loading={loading}
          >
            Upload File
          </Button>
        </AntdUpload>
        <Popconfirm
          title={`Are you sure to delete "${selectedPath?.split("/").pop()}"?`}
          description="This action cannot be undone."
          placement="bottomRight"
          okText="Delete"
          okButtonProps={{ danger: true, type: "primary" }}
          cancelText="Cancel"
          onConfirm={deleteSelected}
          disabled={disabled || !selectedPath}
        >
          <Button
            size="small"
            type="text"
            icon={<CarbonIcon icon={<TrashCan />} />}
            disabled={disabled || !selectedPath}
          >
            Delete
          </Button>
        </Popconfirm>
      </Space>
    </>
  );
};
