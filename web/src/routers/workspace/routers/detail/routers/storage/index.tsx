import { FC, useEffect, useRef, useState } from "react";
import { Breadcrumb, Space, Table } from "antd";

import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { DocumentBlank, Folder, FolderParent } from "@carbon/icons-react";
import { Actions } from "@lepton-dashboard/routers/workspace/routers/detail/routers/storage/components/actions";
import { Card } from "@lepton-dashboard/routers/workspace/components/card";
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
  useDocumentTitle("Storage");
  const [loading, setLoading] = useState(true);
  const [toutchTime, setToutchTime] = useState(0);
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
              <CarbonIcon icon={<DocumentBlank />} />
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
            disabled={loading}
            path={path}
            selectedPath={selectedPath}
            files={files}
            refresh={() => refreshRef.current.next(null)}
          />
        }
        title={
          <Breadcrumb
            items={
              navigatePaths.length < 3
                ? navigatePaths.map((path, i) => {
                    return {
                      title:
                        i === 0 ? (
                          <a href="#" title={path}>
                            <CarbonIcon icon={<Folder />} />
                          </a>
                        ) : (
                          <a href="#" title={path}>
                            {path.split("/").pop()}
                          </a>
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
                          title: (
                            <a href="#" title={path}>
                              <CarbonIcon icon={<Folder />} />
                            </a>
                          ),
                          onClick: () => {
                            setPath(path);
                          },
                        }
                      : {
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
          `}
          loading={loading}
          pagination={false}
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
                setToutchTime(new Date().getTime());
              },
              onTouchEnd: () => {
                if (new Date().getTime() - toutchTime < 100) {
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
