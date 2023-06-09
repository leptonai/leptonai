import { FC } from "react";
import styled from "@emotion/styled";
import { css } from "@emotion/react";
import { useAntdTheme } from "@lepton-dashboard/hooks/use-antd-theme";
import { Avatar, Button, Dropdown, Space } from "antd";

import { GithubOutlined, ReadOutlined } from "@ant-design/icons";
import { Logo } from "@lepton-dashboard/components/logo";
import { useInject } from "@lepton-libs/di";
import { ProfileService } from "@lepton-dashboard/services/profile.service";
import { AuthService } from "@lepton-dashboard/services/auth.service";
import { useNavigate } from "react-router-dom";
import { CarbonIcon } from "@lepton-dashboard/components/icons";
import { Logout } from "@carbon/icons-react";
import { WorkspaceSwitch } from "../workspace-switch";

const Container = styled.div`
  height: 50px;
  padding: 0 24px;
  display: flex;
  flex: 0 0 50px;
  flex-wrap: wrap;
  overflow: hidden;
  z-index: 2;
`;

const MenuContainer = styled.div`
  flex: 1 1 auto;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: end;
`;

export const Header: FC = () => {
  const theme = useAntdTheme();
  const profileService = useInject(ProfileService);
  const authService = useInject(AuthService);
  const navigate = useNavigate();
  return (
    <Container
      css={css`
        background: ${theme.colorBgContainer};
      `}
    >
      <div
        css={css`
          height: 100%;
          display: flex;
        `}
      >
        <Logo />
        <WorkspaceSwitch />
      </div>

      <MenuContainer>
        <Space>
          <Button
            rel="noreferrer"
            href="https://www.lepton.ai"
            target="_blank"
            type="text"
            icon={<ReadOutlined />}
          />
          <Button
            type="text"
            rel="noreferrer"
            href="https://github.com/leptonai"
            target="_blank"
            icon={<GithubOutlined />}
          />
          {profileService.profile?.oauth?.id ? (
            <Dropdown
              menu={{
                items: [
                  {
                    icon: <CarbonIcon icon={<Logout />} />,
                    label: (
                      <div
                        css={css`
                          margin-left: 8px;
                        `}
                      >
                        Logout
                      </div>
                    ),
                    key: "logout",
                    onClick: () =>
                      authService.logout().then(() => {
                        navigate("/login", { relative: "route" });
                      }),
                  },
                ],
              }}
            >
              <Button
                type="text"
                css={css`
                  padding: 4px 6px;
                `}
                icon={
                  <Avatar
                    css={css`
                      position: relative;
                      top: -1px;
                      margin-right: 4px;
                    `}
                    size={18}
                    onError={() => true}
                    src={
                      <img
                        src={
                          profileService.profile?.oauth?.user_metadata
                            .avatar_url
                        }
                        alt="avatar"
                      />
                    }
                  >
                    test
                  </Avatar>
                }
              >
                {profileService.profile?.identification?.email}
              </Button>
            </Dropdown>
          ) : null}
        </Space>
      </MenuContainer>
    </Container>
  );
};
