#include <gazebo/common/Events.hh>
#include <gazebo/gui/GuiPlugin.hh>
#include <gazebo/rendering/Grid.hh>
#include <gazebo/rendering/ogre_gazebo.h>
#include <gazebo/rendering/RenderingIface.hh>
#include <gazebo/rendering/Scene.hh>

namespace gazebo
{
class GreenhouseGridPlugin final : public GUIPlugin
{
  public: GreenhouseGridPlugin()
  {
    this->setFixedSize(0, 0);
    this->setAttribute(Qt::WA_TransparentForMouseEvents);
  }

  public: void Load(sdf::ElementPtr) override
  {
    this->renderConnection = event::Events::ConnectPreRender(
        [this]() { this->ConfigureGrid(); });
  }

  private: void ConfigureGrid()
  {
    if (this->configured)
      return;

    auto scene = rendering::get_scene();
    if (!scene || scene->GridCount() == 0)
      return;

    auto grid = scene->GetGrid(0);
    if (!grid)
      return;

    // The greenhouse footprint is 63 x 44.15 m. Extend every side by
    // (64 - 44.15) / 2 = 9.925 m while keeping 1 m square cells.
    grid->Enable(false);
    this->CreateRectangularGrid(scene);
    this->configured = true;
    this->renderConnection.reset();
  }

  private: void CreateRectangularGrid(rendering::ScenePtr _scene)
  {
    constexpr double halfX = 41.425;
    constexpr double halfY = 32.0;
    const auto color = ignition::math::Color(0.3f, 0.3f, 0.3f, 0.5f);
    const std::string materialName = "GreenhouseReferenceGridMaterial";

    Ogre::MaterialPtr material = Ogre::MaterialManager::getSingleton().create(
        materialName, Ogre::ResourceGroupManager::DEFAULT_RESOURCE_GROUP_NAME);
    material->setDiffuse(Ogre::ColourValue(color.R(), color.G(), color.B(), color.A()));
    material->setAmbient(Ogre::ColourValue(color.R(), color.G(), color.B(), color.A()));
    material->setSceneBlending(Ogre::SBT_TRANSPARENT_ALPHA);
    material->setDepthWriteEnabled(false);
    material->setDepthCheckEnabled(true);
    material->getTechnique(0)->setLightingEnabled(false);

    this->gridVisual.reset(new rendering::Visual(
        "GreenhouseReferenceGrid", _scene->WorldVisual(), false));
    this->gridVisual->Load();

    Ogre::SceneManager *manager = _scene->OgreSceneManager();
    this->gridLines = manager->createManualObject("GreenhouseReferenceGridLines");
    this->gridLines->setVisibilityFlags(GZ_VISIBILITY_GUI);
    this->gridLines->setCastShadows(false);
    this->gridLines->setDynamic(false);
    this->gridVisual->GetSceneNode()->attachObject(this->gridLines);
    this->gridLines->begin(materialName, Ogre::RenderOperation::OT_LINE_LIST);

    auto addLine = [this, &color](double x1, double y1, double x2, double y2)
    {
      this->gridLines->position(x1, y1, 0.015);
      this->gridLines->colour(color.R(), color.G(), color.B(), color.A());
      this->gridLines->position(x2, y2, 0.015);
      this->gridLines->colour(color.R(), color.G(), color.B(), color.A());
    };

    for (int x = -41; x <= 41; ++x)
      addLine(x, -halfY, x, halfY);
    addLine(-halfX, -halfY, -halfX, halfY);
    addLine(halfX, -halfY, halfX, halfY);
    for (int y = -32; y <= 32; ++y)
      addLine(-halfX, y, halfX, y);

    this->gridLines->end();
  }

  private: bool configured{false};
  private: event::ConnectionPtr renderConnection;
  private: rendering::VisualPtr gridVisual;
  private: Ogre::ManualObject *gridLines{nullptr};
};

GZ_REGISTER_GUI_PLUGIN(GreenhouseGridPlugin)
}
