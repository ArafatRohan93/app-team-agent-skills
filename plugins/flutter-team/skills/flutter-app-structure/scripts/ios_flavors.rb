# Adds Debug-/Release-/Profile-<flavor> build configurations to an Xcode
# project, each backed by its own Flutter/<Config>-<flavor>.xcconfig, and sets
# per-flavor PRODUCT_BUNDLE_IDENTIFIER and FLAVOR_APP_NAME on the Runner target.
# Idempotent: existing configurations are left alone.
#
# Usage: ruby ios_flavors.rb <ios_dir> '<json>'
#   json: {"flavors":[{"name":"development","suffix":".dev","app_name":"[DEV] App"}, ...],
#          "default_app_name":"App"}
#
# Requires the `xcodeproj` gem (installed with CocoaPods).
require 'json'

begin
  require 'xcodeproj'
rescue LoadError
  warn 'The xcodeproj gem is missing. Install it with `gem install xcodeproj` (it ships with CocoaPods).'
  exit 2
end

ios_dir, spec_json = ARGV
abort 'usage: ruby ios_flavors.rb <ios_dir> <json>' unless ios_dir && spec_json
spec = JSON.parse(spec_json)

project = Xcodeproj::Project.open(File.join(ios_dir, 'Runner.xcodeproj'))
runner = project.targets.find { |t| t.name == 'Runner' } or abort 'Runner target not found'
flutter_group = project.main_group['Flutter'] or abort 'Flutter group not found'

base_bundle_id = runner.build_configuration_list['Release'].build_settings['PRODUCT_BUNDLE_IDENTIFIER']
bases = %w[Debug Release Profile]

# Plain Debug/Release/Profile keep working (e.g. the Runner scheme).
bases.each do |base|
  runner.build_configuration_list[base].build_settings['FLAVOR_APP_NAME'] = spec['default_app_name']
end

spec['flavors'].each do |flavor|
  bases.each do |base|
    name = "#{base}-#{flavor['name']}"
    xcconfig = "#{name}.xcconfig"
    xcconfig_path = File.join(ios_dir, 'Flutter', xcconfig)
    unless File.exist?(xcconfig_path)
      File.write(xcconfig_path, <<~XCCONFIG)
        #include? "Pods/Target Support Files/Pods-Runner/Pods-Runner.#{name.downcase}.xcconfig"
        #include "Generated.xcconfig"
      XCCONFIG
    end
    # The Flutter group has no path of its own; its children carry
    # "Flutter/<file>" paths relative to ios/ — match that.
    ref = flutter_group.files.find { |f| f.display_name == xcconfig } ||
          flutter_group.new_reference(File.expand_path(xcconfig_path))
    ref.name = xcconfig
    ref.path = "Flutter/#{xcconfig}"

    [project, *project.targets].each do |owner|
      list = owner.build_configuration_list
      next if list[name]

      source = list[base] or next
      config = project.new(Xcodeproj::Project::Object::XCBuildConfiguration)
      config.name = name
      config.build_settings = Marshal.load(Marshal.dump(source.build_settings))
      config.base_configuration_reference = source.base_configuration_reference

      if owner.equal?(runner)
        config.base_configuration_reference = ref
        config.build_settings['PRODUCT_BUNDLE_IDENTIFIER'] = "#{base_bundle_id}#{flavor['suffix']}"
        config.build_settings['FLAVOR_APP_NAME'] = flavor['app_name']
      end

      list.build_configurations << config
    end
  end
end

project.save
puts "iOS: base bundle id #{base_bundle_id}; configurations added for #{spec['flavors'].map { |f| f['name'] }.join(', ')}"
