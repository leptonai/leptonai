import { Link } from "@lepton-dashboard/components/link";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { WorkspaceTrackerService } from "@lepton-dashboard/services/workspace-tracker.service";
import { FC, useEffect, useRef, useState } from "react";
import { Breadcrumb, Empty, Space, Table } from "antd";

import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Document, Folder, FolderParent } from "@carbon/icons-react";
import { Actions } from "@lepton-dashboard/routers/workspace/routers/detail/routers/storage/components/actions";
import { Card } from "../../../../../../components/card";
import { useInject } from "@lepton-libs/di";
import { useDocumentTitle } from "@lepton-dashboard/hooks/use-document-title";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { ColumnsType } from "antd/es/table";
import { FileManagerService } from "@lepton-dashboard/routers/workspace/services/file-manager.service";
import { FileInfo } from "@lepton-dashboard/interfaces/storage";
import { useObservableFromState } from "@lepton-libs/hooks/use-observable-from-state";
import { BehaviorSubject, combineLatestWith, map, switchMap } from "rxjs";
import { css } from "@emotion/react";

type UIFileInfo = FileInfo & {
  key?: "parent-dir";
};

const generateNavigatePaths = (path: string): string[] => {
  const paths = path.split("/");
  return paths.map((_, i) => {
    return paths.slice(0, i + 1).join("/");
  });
};

export const Storage: FC = () => {
  const theme = useAntdTheme();
  useDocumentTitle("Storage");
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const [loading, setLoading] = useState(true);
  const [touchTime, setTouchTime] = useState(0);
  const [path, setPath] = useState<string>("");
  const [navigatePaths, setNavigatePaths] = useState<string[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | undefined>();
  const path$ = useObservableFromState(path);
  const refreshRef = useRef(new BehaviorSubject<null>(null));
  const fileManagerService: FileManagerService<FileInfo> =
    useInject(FileManagerService);
  const files: UIFileInfo[] = useStateFromObservable(
    () =>
      refreshRef.current.pipe(
        combineLatestWith(path$),
        map(([, path]) => path),
        switchMap((path) => {
          setLoading(true);
          if (path === "") {
            return fileManagerService.list();
          } else {
            return fileManagerService
              .list({
                path,
                type: "dir",
                name: path.split("/").pop() || "",
              })
              .pipe(
                map((files: UIFileInfo[]) => {
                  files.unshift({
                    type: "dir",
                    name: "..",
                    path: path.split("/").slice(0, -1).join("/"),
                    key: "parent-dir",
                  });
                  return files;
                })
              );
          }
        })
      ),
    [],
    {
      next: () => setLoading(false),
      error: () => setLoading(false),
    }
  );

  useEffect(() => {
    if (selectedPath !== undefined) {
      const selectedFile = files.find((file) => file.path === selectedPath);
      if (!selectedFile) {
        setSelectedPath(undefined);
      }
    }
  }, [files, selectedPath]);

  useEffect(() => {
    const navigatePaths = generateNavigatePaths(path);
    setNavigatePaths(navigatePaths);
  }, [path]);

  const columns: ColumnsType<UIFileInfo> = [
    {
      title: (
        <span
          css={css`
            margin-left: 22px;
          `}
        >
          Name
        </span>
      ),
      dataIndex: "name",
      render: (name: string, record) => {
        if (record.type === "dir") {
          return (
            <Space
              css={css`
                cursor: pointer;
              `}
              onClick={() => {
                setPath(record.path);
              }}
              title={record.path}
            >
              {record.key === "parent-dir" ? (
                <CarbonIcon icon={<FolderParent />} />
              ) : (
                <CarbonIcon icon={<Folder />} />
              )}
              <span>{name}</span>
            </Space>
          );
        } else {
          return (
            <Space title={record.path}>
              <CarbonIcon icon={<Document />} />
              <span>{name}</span>
            </Space>
          );
        }
      },
    },
  ];

  return (
    <>
      <Card
        extra={
          <Actions
            disabled={loading || workspaceTrackerService.workspace?.isPastDue}
            path={path}
            selectedPath={selectedPath}
            files={files}
            refresh={() => refreshRef.current.next(null)}
          />
        }
        titleOverflowHidden
        title={
          <Breadcrumb
            css={css`
              margin-left: 8px;
              a.ant-breadcrumb-link {
                font-weight: normal !important;
                color: ${theme.colorText} !important;
              }
              .ant-breadcrumb-link > .anticon + span {
                margin-inline-start: 8px !important;
              }
              & > ol {
                flex-wrap: nowrap;
                & > li {
                  flex: 0 1 auto;
                  overflow: hidden;

                  .ant-breadcrumb-overlay-link,
                  a {
                    margin-inline: 0;
                    display: flex;
                  }

                  &.ant-breadcrumb-separator {
                    flex: 0 0 auto;
                  }
                  .ant-breadcrumb-link {
                    white-space: nowrap;
                  }
                  & > .ant-dropdown-trigger {
                    .ant-breadcrumb-link {
                      overflow: hidden;
                    }
                  }
                  & > .ant-breadcrumb-overlay-link {
                    flex-wrap: nowrap;
                  }
                }
              }
            `}
            items={
              navigatePaths.length < 3
                ? navigatePaths.map((path, i) => {
                    return {
                      href: "#",
                      title:
                        i === 0 ? (
                          <>
                            <CarbonIcon icon={<Folder />} />
                            <span>Storage</span>
                          </>
                        ) : (
                          <>{path.split("/").pop()}</>
                        ),
                      onClick: () => {
                        setPath(path);
                      },
                    };
                  })
                : [
                    navigatePaths[0],
                    navigatePaths[navigatePaths.length - 1],
                  ].map((path, i) => {
                    return i === 0
                      ? {
                          href: "#",
                          title: (
                            <>
                              <CarbonIcon icon={<Folder />} />
                              <span>Storage</span>
                            </>
                          ),
                          onClick: () => {
                            setPath(path);
                          },
                        }
                      : {
                          href: "#",
                          title: path.split("/").pop(),
                          onClick: () => {
                            setPath(path);
                          },
                          menu: {
                            items: navigatePaths
                              .slice(1, navigatePaths.length - 1)
                              .reverse()
                              .map((path, i) => {
                                return {
                                  key: i,
                                  label: (
                                    <span title={path}>
                                      {path.split("/").pop()}
                                    </span>
                                  ),
                                  onClick: () => {
                                    setPath(path);
                                  },
                                };
                              }),
                          },
                        };
                  })
            }
          />
        }
      >
        <Table
          css={css`
            thead tr td:first-of-type::before {
              display: none;
            }
            .ant-table-placeholder {
              .ant-table-cell {
                border-bottom: none;
              }
            }
          `}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <>
                    <Link
                      to="https://www.lepton.ai/docs/advanced/storage"
                      target="_blank"
                    >
                      No files found, learn more about storage
                    </Link>
                  </>
                }
              />
            ),
          }}
          loading={loading}
          pagination={false}
          showHeader={false}
          size="small"
          columns={columns}
          dataSource={files}
          rowClassName={(record) => {
            if (record.path === selectedPath) {
              return "ant-table-row-selected";
            } else {
              return "";
            }
          }}
          onRow={(record) => {
            return {
              onTouchStart: () => {
                setTouchTime(new Date().getTime());
              },
              onTouchEnd: () => {
                if (new Date().getTime() - touchTime < 100) {
                  if (record.type === "dir") {
                    setPath(record.path);
                  }
                } else {
                  if (record.key !== "parent-dir") {
                    setSelectedPath(record.path);
                  }
                }
              },
              onDoubleClick: () => {
                if (record.type === "dir") {
                  setPath(record.path);
                }
              },
              onClick: () => {
                if (record.key !== "parent-dir") {
                  setSelectedPath(record.path);
                }
              },
            };
          }}
          rowKey="name"
        />
      </Card>
    </>
  );
};
