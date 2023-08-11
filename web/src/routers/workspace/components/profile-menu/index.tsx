import { useInject } from "@lepton-libs/di";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { Button, Dropdown, Space, Grid } from "antd";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import {
  ChevronDown,
  DataEnrichment,
  Logout,
  UserProfile,
} from "@carbon/icons-react";
import { FC } from "react";
import { NavigateService } from "@lepton-dashboard/services/navigate.service";

export const ProfileMenu: FC = () => {
  const profileService = useInject(ProfileService);
  const authService = useInject(AuthService);
  const navigateService = useInject(NavigateService);
  const { xs } = Grid.useBreakpoint();

  return (
    <>
      {profileService.profile?.identification?.id ? (
        <Dropdown
          menu={{
            items: [
              {
                icon: <DataEnrichment />,
                label: "Getting Started",
                key: "getting-started",
                onClick: () => {
                  navigateService.navigateTo(`gettingStarted`);
                },
              },
              {
                icon: <Logout />,
                label: "Logout",
                key: "logout",
                onClick: () =>
                  authService.logout().subscribe(() => {
                    navigateService.navigateTo("login", {
                      relative: "route",
                    });
                  }),
              },
            ],
          }}
        >
          <Button size="small" type="text">
            <Space>
              <CarbonIcon icon={<UserProfile />} />
              {xs ? null : (
                <span>{profileService.profile?.identification?.email}</span>
              )}
              <CarbonIcon icon={<ChevronDown />} />
            </Space>
          </Button>
        </Dropdown>
      ) : (
        <Button
          type="text"
          size="small"
          icon={<CarbonIcon icon={<Logout />} />}
          onClick={() => {
            authService.logout().subscribe(() => {
              navigateService.navigateTo("login", {
                relative: "route",
              });
            });
          }}
        >
          Logout
        </Button>
      )}
    </>
  );
};
