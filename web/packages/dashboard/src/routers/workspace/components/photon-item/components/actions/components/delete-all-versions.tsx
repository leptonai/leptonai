import { Photon, PhotonVersion } from "@lepton-dashboard/interfaces/photon";
import { Button, message, Popconfirm, Space, Tooltip } from "antd";
import { Deployment } from "@lepton-dashboard/interfaces/deployment";
import { FC, useMemo, useState } from "react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { StopFilled, TrashCan } from "@carbon/icons-react";
import { concat, Subject, takeUntil, tap } from "rxjs";
import { useInject } from "@lepton-libs/di";
import { PhotonService } from "@lepton-dashboard/routers/workspace/services/photon.service";

interface DeleteAllVersionsProps {
  photon: Photon;
  relatedDeployments: Deployment[];
  versions: PhotonVersion[];
  disabled?: boolean;
  onDeleted?: (name: string) => void;
}
export const DeleteAllVersions: FC<DeleteAllVersionsProps> = ({
  photon,
  disabled = false,
  relatedDeployments,
  versions,
  onDeleted = () => void 0,
}) => {
  const photonService = useInject(PhotonService);
  const [deleting, setDeleting] = useState(false);
  const [cancelDelete, setCancelDelete] = useState<Subject<void> | null>(null);

  const deleteAllVersions = () => {
    const cancel$ = new Subject<void>();
    const queue = versions.map((v) => v.id);
    const total = queue.length;
    let done = 0;

    setDeleting(true);
    setCancelDelete(cancel$);
    const updateProgress = () => {
      void message.loading({
        type: "loading",
        content: (
          <Space>
            <span>
              Deleting {done}/{total} versions of {photon.name}
            </span>
            <Button
              type="link"
              size="small"
              onClick={() => {
                cancel$.next();
                cancel$.complete();
              }}
            >
              cancel
            </Button>
          </Space>
        ),
        key: "delete-photon",
        duration: 0,
      });
    };
    updateProgress();

    concat(
      ...queue.map((v) =>
        photonService.delete(v).pipe(
          tap({
            next: () => {
              done++;
              onDeleted(v);
            },
          })
        )
      )
    )
      .pipe(takeUntil(cancel$))
      .subscribe({
        next: () => {
          if (done === total) {
            void message.success({
              type: "success",
              content: `Deleted ${
                total > 1 ? `${total} versions` : `${total} version`
              } of ${photon.name}`,
              key: "delete-photon",
            });
          } else {
            updateProgress();
          }
        },
        error: () => {
          const count = total - done;
          void message.error({
            type: "error",
            content: `Failed to delete ${
              count > 1 ? `${count} versions` : `${count} version`
            } of ${photon.name}`,
            key: "delete-photon",
          });
          setDeleting(false);
          cancel$.complete();
        },
        complete: () => {
          setDeleting(false);

          if (cancel$.closed) {
            message.destroy("delete-photon");
          }

          cancel$.complete();
        },
      });
  };

  const deleteAllButton = useMemo(
    () => (
      <Button
        disabled={disabled || relatedDeployments.length > 0}
        size="small"
        type="text"
        icon={<CarbonIcon icon={<TrashCan />} />}
      >
        Delete
      </Button>
    ),
    [disabled, relatedDeployments]
  );
  return deleting ? (
    <Button
      size="small"
      type="text"
      icon={<CarbonIcon icon={<StopFilled />} />}
      onClick={() => {
        cancelDelete?.next();
        cancelDelete?.complete();
      }}
    >
      Cancel
    </Button>
  ) : (
    <Popconfirm
      disabled={disabled || relatedDeployments.length > 0}
      title="Delete all versions of the photon"
      description="Are you sure to delete all versions of this photon?"
      onConfirm={deleteAllVersions}
    >
      {relatedDeployments.length > 0 ? (
        <Tooltip title="Cannot delete a currently deployed version">
          {deleteAllButton}
        </Tooltip>
      ) : (
        deleteAllButton
      )}
    </Popconfirm>
  );
};
