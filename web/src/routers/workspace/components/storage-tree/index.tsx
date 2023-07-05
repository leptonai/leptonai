import { FileInfo } from "@lepton-dashboard/interfaces/storage";
import { FC, ReactNode, useCallback, useMemo, useRef } from "react";
import {
  DirectoryItem,
  FileEntry,
  FileManagerService,
  FileTreeControl,
} from "@lepton-dashboard/routers/workspace/services/file-manager.service";
import { useInject } from "@lepton-libs/di";
import { useStateFromObservable } from "@lepton-libs/hooks/use-state-from-observable";
import { map } from "rxjs";
import { Tree } from "antd";
import { Document, Folder } from "@carbon/icons-react";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { LoadingOutlined } from "@ant-design/icons";

export interface StorageTreeProps {
  nodeFilter?: (item: FileInfo) => boolean;
  nodeDisabler?: (item: FileInfo) => boolean;
  onInitialized?: () => void;
  onInitializedFailed?: (err: unknown) => void;
  onSelectedKeysChanged?: (keys: string[]) => void;
  disabled?: boolean;
}

interface TreeNodeBase {
  icon: ReactNode;
  key: string;
  title: ReactNode;
  disabled: boolean;
  raw: FileInfo;
}

interface TreeNodeLeaf extends TreeNodeBase {
  isLeaf: true;
}

interface TreeNodeParent extends TreeNodeBase {
  isLeaf: false;
  children: TreeNode[];
}

type TreeNode = TreeNodeLeaf | TreeNodeParent;

export const StorageTree: FC<StorageTreeProps> = ({
  onInitialized = () => void 0,
  onInitializedFailed = () => void 0,
  onSelectedKeysChanged = () => void 0,
  nodeFilter = () => true,
  nodeDisabler = () => false,
  disabled,
}) => {
  const fileManagerService: FileManagerService<FileInfo> =
    useInject(FileManagerService);
  const treeControl = useRef(
    new FileTreeControl(fileManagerService, {
      selectionMode: "single",
      expansionMode: "multiple",
      trackBy: (item) => item.path,
      isExpandable: (item): item is DirectoryItem<FileInfo> =>
        item.type === "dir",
    })
  );

  const data = useStateFromObservable(() => treeControl.current.connect(), [], {
    next: () => {
      onInitialized();
    },
    error: (err) => {
      onInitializedFailed(err);
    },
  });

  const expansions = useStateFromObservable(
    () =>
      treeControl.current.expansionModel.changed.pipe(
        map(() => treeControl.current.expansionModel.selected)
      ),
    []
  );

  const loadings = useStateFromObservable(
    () =>
      treeControl.current.loadingModel.changed.pipe(
        map(() => treeControl.current.loadingModel.selected)
      ),
    []
  );

  const selectedKeys = useStateFromObservable(
    () =>
      treeControl.current.selectionModel!.changed.pipe(
        map(() => treeControl.current.selectionModel!.selected)
      ),
    [],
    {
      next: (keys) => {
        onSelectedKeysChanged(keys);
      },
    }
  );

  const treeData: TreeNode[] = useMemo(() => {
    const toTreeData = (files: readonly FileEntry<FileInfo>[]): TreeNode[] => {
      return files.filter(nodeFilter).map((value) => {
        const isLoading = loadings.includes(value.path);
        return {
          disabled: nodeDisabler(value),
          title: value.name,
          icon:
            value.type === "dir" ? (
              isLoading ? (
                <LoadingOutlined />
              ) : (
                <CarbonIcon icon={<Folder />} />
              )
            ) : (
              <CarbonIcon icon={<Document />} />
            ),
          isLeaf: value.type === "file",
          children: treeControl.current.isExpandable(value)
            ? toTreeData(value.children || [])
            : undefined,
          key: value.path,
          raw: value,
        } as TreeNode;
      });
    };
    return toTreeData(data);
  }, [data, nodeFilter, loadings, nodeDisabler]);

  const onExpand = useCallback((node: TreeNode) => {
    treeControl.current.toggle(node.raw);
  }, []);

  const onSelect = useCallback((node: TreeNode) => {
    if (node.disabled) {
      return;
    }
    treeControl.current.select(node.raw);
  }, []);

  return (
    <div>
      <Tree.DirectoryTree
        showIcon
        disabled={disabled}
        expandAction="doubleClick"
        treeData={treeData}
        expandedKeys={expansions}
        selectedKeys={selectedKeys}
        onExpand={(_, info) => onExpand(info.node)}
        onSelect={(_, info) => onSelect(info.node)}
      />
    </div>
  );
};

export default StorageTree;
