import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { useInject } from "@lepton-libs/di";
import { FC, PropsWithChildren } from "react";
import { useParams } from "react-router-dom";
import { WorkspaceTrackerService } from "../../../../services/workspace-tracker.service";
import { NavigateTo } from "@lepton-dashboard/components/navigate-to";

export const Validate: FC<PropsWithChildren> = ({ children }) => {
  const profileService = useInject(ProfileService);
  const workspaceTrackerService = useInject(WorkspaceTrackerService);
  const { workspaceId } = useParams();

  if (
    profileService.profile &&
    profileService.profile.authorized_workspaces.some(
      (e) => e.auth.id === workspaceId
    )
  ) {
    workspaceTrackerService.trackWorkspace(workspaceId!);
    return <>{children}</>;
  } else {
    const firstId = profileService.profile!.authorized_workspaces[0].auth.id;
    workspaceTrackerService.trackWorkspace(firstId);
    return (
      <NavigateTo
        name="workspace"
        params={{
          workspaceId: firstId,
        }}
        replace
      />
    );
  }
};
