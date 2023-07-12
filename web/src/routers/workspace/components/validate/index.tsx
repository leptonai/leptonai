import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { FC, PropsWithChildren } from "react";
import { useParams } from "react-router-dom";
import { WorkspaceTrackerService } from "../../../../services/workspace-tracker.service";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

export const Validate: FC<PropsWithChildren> = ({ children }) => {
  const profileService = useInject(ProfileService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const { workspaceName } = useParams();

  if (
    profileService.profile &&
    profileService.profile.authorized_workspaces.some(
      (e) => e.data.workspace_name === workspaceName
    )
  ) {
    workspaceTrackerService.trackWorkspace(workspaceName!);
    return <>{children}</>;
  } else {
    const firstWorkspaceName =
      profileService.profile!.authorized_workspaces[0].data.workspace_name;
    workspaceTrackerService.trackWorkspace(firstWorkspaceName);
    return (
      <NavigateTo
        name="workspace"
        params={{
          workspaceId: firstWorkspaceName,
        }}
        replace
      />
    );
  }
};
